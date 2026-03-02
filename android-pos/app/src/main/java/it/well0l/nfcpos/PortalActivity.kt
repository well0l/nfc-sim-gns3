package it.well0l.nfcpos

import android.annotation.SuppressLint
import android.app.AlertDialog
import android.content.Context
import android.net.http.SslError
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.webkit.CookieManager
import android.webkit.SslErrorHandler
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity

class PortalActivity : AppCompatActivity(), NfcAdapter.ReaderCallback {

    private lateinit var webView: WebView
    private var nfcAdapter: NfcAdapter? = null

    private val handler = Handler(Looper.getMainLooper())

    private var nfcEnabledForPage: Boolean = false
    private var processing: Boolean = false

    private fun prefs() = getSharedPreferences("nfc_portal", Context.MODE_PRIVATE)
    private fun baseUrl(): String = (prefs().getString("base_url", "https://10.10.100.10/") ?: "https://10.10.100.10/").trim()

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_portal)

        nfcAdapter = NfcAdapter.getDefaultAdapter(this)

        webView = findViewById(R.id.webView)

        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true)

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.cacheMode = WebSettings.LOAD_DEFAULT
        webView.settings.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                return false
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                if (url != null) {
                    nfcEnabledForPage = isBarContextUrl(url)
                    updateNfcReaderState()
                    injectNfcBridge()
                }
            }

            override fun onReceivedSslError(view: WebView?, handler: SslErrorHandler?, error: SslError?) {
                if (BuildConfig.DEBUG) {
                    handler?.proceed()
                } else {
                    handler?.cancel()
                }
            }
        }

        webView.setOnLongClickListener {
            showUrlDialog()
            true
        }

        webView.loadUrl(baseUrl())
    }

    override fun onResume() {
        super.onResume()
        updateNfcReaderState()
    }

    override fun onPause() {
        super.onPause()
        disableReader()
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }

    private fun isBarContextUrl(url: String): Boolean {
        return url.contains("/service/bar") || url.contains("/bar/")
    }

    private fun updateNfcReaderState() {
        val adapter = nfcAdapter
        if (!nfcEnabledForPage || adapter == null || !adapter.isEnabled || processing) {
            disableReader()
            return
        }
        adapter.enableReaderMode(
            this,
            this,
            NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_NFC_B or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK,
            null
        )
    }

    private fun disableReader() {
        nfcAdapter?.disableReaderMode(this)
    }

    override fun onTagDiscovered(tag: Tag) {
        if (!nfcEnabledForPage) return
        if (processing) return
        processing = true
        disableReader()

        val uid = bytesToHex(tag.id)

        handler.post {
            val js = "(function(){ try { if (typeof window.__onNfcUid === 'function') window.__onNfcUid('$uid'); } catch(e){} })();"
            webView.evaluateJavascript(js, null)
        }

        handler.postDelayed({
            processing = false
            updateNfcReaderState()
        }, 1200)
    }

    private fun injectNfcBridge() {
        val js = """
            (function(){
              try {
                if (window.__nfc_bridge_installed) return;
                window.__nfc_bridge_installed = true;

                // Called by Android (top window). Forward UID to iframe if present.
                window.__onNfcUid = function(uid){
                  try {
                    var fr = document.querySelector('iframe');
                    if (fr && fr.contentWindow) {
                      if (typeof fr.contentWindow.__onNfcUid === 'function') {
                        fr.contentWindow.__onNfcUid(uid);
                        return;
                      }
                      fr.contentWindow.postMessage({type:'nfc_uid', uid: uid}, '*');
                      return;
                    }
                  } catch(e) {}
                };
              } catch(e) {}
            })();
        """.trimIndent()

        webView.evaluateJavascript(js, null)
    }

    private fun showUrlDialog() {
        val input = EditText(this).apply {
            hint = "https://IP_DEL_PC/"
            setText(baseUrl())
            inputType = InputType.TYPE_CLASS_TEXT
        }

        AlertDialog.Builder(this)
            .setTitle("Base URL portal")
            .setMessage("Long-press sulla pagina per modificare l'URL.\nIn debug accettiamo cert self-signed.")
            .setView(input)
            .setNegativeButton("Annulla", null)
            .setPositiveButton("Salva") { _, _ ->
                prefs().edit().putString("base_url", input.text.toString().trim()).apply()
                webView.loadUrl(baseUrl())
            }
            .show()
    }

    private fun bytesToHex(bytes: ByteArray): String {
        val sb = StringBuilder(bytes.size * 2)
        for (b in bytes) sb.append(String.format("%02X", b))
        return sb.toString()
    }
}

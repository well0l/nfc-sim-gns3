package it.well0l.nfcpos

import android.app.AlertDialog
import android.content.Context
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.widget.Button
import android.widget.EditText
import android.widget.GridLayout
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.security.SecureRandom
import java.util.Locale
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

class MainActivity : AppCompatActivity(), NfcAdapter.ReaderCallback {

    private val http = OkHttpClient()

    private lateinit var title: TextView
    private lateinit var amountDisplay: TextView
    private lateinit var keypad: GridLayout
    private lateinit var confirmButton: Button
    private lateinit var cancelButton: Button
    private lateinit var status: TextView

    private var amountDigits: String = "" // centesimi come stringa di cifre
    private var waitingNfc: Boolean = false
    private var processing: Boolean = false

    private var nfcAdapter: NfcAdapter? = null

    private val handler = Handler(Looper.getMainLooper())
    private var timeoutRunnable: Runnable? = null

    private fun prefs() = getSharedPreferences("nfc_pos", Context.MODE_PRIVATE)

    private fun backendBaseUrl(): String = prefs().getString("base_url", "http://10.10.100.10:8080")!!.trimEnd('/')
    private fun hmacSecret(): String = prefs().getString("hmac_secret", "change_me_in_production")!!
    private fun deviceId(): String = prefs().getString("device_id", "bar-android")!!

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        title = findViewById(R.id.title)
        amountDisplay = findViewById(R.id.amountDisplay)
        keypad = findViewById(R.id.keypad)
        confirmButton = findViewById(R.id.confirmButton)
        cancelButton = findViewById(R.id.cancelButton)
        status = findViewById(R.id.status)

        nfcAdapter = NfcAdapter.getDefaultAdapter(this)

        bindKeypad()
        updateDisplay()

        confirmButton.setOnClickListener {
            if (nfcAdapter == null) {
                setStatus("NFC non disponibile su questo device.")
                return@setOnClickListener
            }
            if (nfcAdapter?.isEnabled != true) {
                setStatus("Attiva NFC nelle impostazioni.")
                return@setOnClickListener
            }

            val cents = amountCents()
            if (cents <= 0) {
                setStatus("Inserisci un importo.")
                return@setOnClickListener
            }
            enterWaitingMode()
        }

        cancelButton.setOnClickListener {
            exitWaitingMode("Attesa annullata.")
        }

        title.setOnLongClickListener {
            showConfigDialog()
            true
        }

        if (nfcAdapter == null) {
            setStatus("NFC non disponibile su questo device.")
            confirmButton.isEnabled = false
        }
    }

    override fun onResume() {
        super.onResume()
        if (waitingNfc && !processing) enableReader()
    }

    override fun onPause() {
        super.onPause()
        disableReader()
    }

    private fun bindKeypad() {
        fun bind(id: Int, onClick: () -> Unit) {
            findViewById<Button>(id).setOnClickListener { onClick() }
        }
        bind(R.id.k0) { addDigit('0') }
        bind(R.id.k1) { addDigit('1') }
        bind(R.id.k2) { addDigit('2') }
        bind(R.id.k3) { addDigit('3') }
        bind(R.id.k4) { addDigit('4') }
        bind(R.id.k5) { addDigit('5') }
        bind(R.id.k6) { addDigit('6') }
        bind(R.id.k7) { addDigit('7') }
        bind(R.id.k8) { addDigit('8') }
        bind(R.id.k9) { addDigit('9') }
        bind(R.id.kC) { clearAmount() }
        bind(R.id.kBk) { backspace() }
    }

    private fun addDigit(d: Char) {
        if (waitingNfc) return
        if (amountDigits.length >= 9) return
        amountDigits += d
        updateDisplay()
    }

    private fun clearAmount() {
        if (waitingNfc) return
        amountDigits = ""
        updateDisplay()
    }

    private fun backspace() {
        if (waitingNfc) return
        if (amountDigits.isNotEmpty()) {
            amountDigits = amountDigits.dropLast(1)
            updateDisplay()
        }
    }

    private fun amountCents(): Int = (amountDigits.ifEmpty { "0" }).toInt()

    private fun amountEuroString(): String {
        val euro = amountCents() / 100.0
        return String.format(Locale.US, "%.2f", euro)
    }

    private fun updateDisplay() {
        amountDisplay.text = "€" + amountEuroString()
    }

    private fun setStatus(msg: String) {
        status.text = msg
    }

    private fun enterWaitingMode() {
        waitingNfc = true
        processing = false
        setKeypadEnabled(false)
        confirmButton.isEnabled = false
        cancelButton.isEnabled = true
        setStatus("Avvicina la carta NFC… (importo €${amountEuroString()})")

        enableReader()
        startTimeout()
    }

    private fun exitWaitingMode(msg: String) {
        waitingNfc = false
        processing = false
        stopTimeout()
        disableReader()
        setKeypadEnabled(true)
        confirmButton.isEnabled = true
        cancelButton.isEnabled = false
        setStatus(msg)
    }

    private fun startTimeout() {
        stopTimeout()
        val r = Runnable {
            if (waitingNfc && !processing) {
                exitWaitingMode("Tempo scaduto: riprova.")
            }
        }
        timeoutRunnable = r
        handler.postDelayed(r, 30_000)
    }

    private fun stopTimeout() {
        timeoutRunnable?.let { handler.removeCallbacks(it) }
        timeoutRunnable = null
    }

    private fun setKeypadEnabled(enabled: Boolean) {
        for (i in 0 until keypad.childCount) {
            keypad.getChildAt(i).isEnabled = enabled
        }
    }

    private fun enableReader() {
        val adapter = nfcAdapter ?: return
        if (!adapter.isEnabled) return
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
        if (!waitingNfc) return
        if (processing) return
        processing = true
        stopTimeout()
        disableReader()

        val uid = bytesToHex(tag.id)
        handler.post { setStatus("Carta letta: $uid — invio transazione…") }

        Thread {
            val result = doPurchase(uid)
            handler.post {
                when (result) {
                    "ok" -> {
                        amountDigits = ""
                        updateDisplay()
                        exitWaitingMode("OK: pagamento completato. Pronto.")
                    }
                    "denied_funds" -> exitWaitingMode("Saldo insufficiente.")
                    "denied_notfound" -> exitWaitingMode("Carta non trovata.")
                    "denied_blocked", "denied_blocked_auto" -> exitWaitingMode("Carta bloccata.")
                    "denied_ratelimit" -> exitWaitingMode("Troppi tentativi, riprova tra poco.")
                    "denied_velocity" -> exitWaitingMode("Transazione sospetta (velocity).")
                    "denied_invalid_token" -> exitWaitingMode("Token non valido (HMAC/ts/nonce).")
                    "denied_replay" -> exitWaitingMode("Replay rilevato (nonce usato).")
                    else -> exitWaitingMode("Errore: $result")
                }
            }
        }.start()
    }

    private fun doPurchase(cardUid: String): String {
        val cents = amountCents()
        val ts = (System.currentTimeMillis() / 1000).toInt()
        val nonce = randomHex(8)
        val dev = deviceId()

        val payload = "$cardUid:$cents:$dev:$ts:$nonce"
        val sig = hmacSha256Hex(hmacSecret(), payload)

        val token = JSONObject()
            .put("ts", ts)
            .put("nonce", nonce)
            .put("sig", sig)

        val body = JSONObject()
            .put("card_uid", cardUid)
            .put("amount", amountEuroString())
            .put("device_id", dev)
            .put("token", token)

        val req = Request.Builder()
            .url(backendBaseUrl() + "/api/purchase")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()

        http.newCall(req).execute().use { resp ->
            val raw = resp.body?.string() ?: "{}"
            return try {
                JSONObject(raw).optString("result", "error")
            } catch (_: Exception) {
                "error_parse"
            }
        }
    }

    private fun showConfigDialog() {
        val p = prefs()

        val base = EditText(this).apply {
            hint = "Base URL backend"
            setText(backendBaseUrl())
            inputType = InputType.TYPE_CLASS_TEXT
        }
        val dev = EditText(this).apply {
            hint = "Device ID"
            setText(deviceId())
            inputType = InputType.TYPE_CLASS_TEXT
        }
        val secret = EditText(this).apply {
            hint = "HMAC secret"
            setText(hmacSecret())
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }

        val wrap = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val pad = (16 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad, pad, pad)
            addView(base)
            addView(dev)
            addView(secret)
        }

        AlertDialog.Builder(this)
            .setTitle("Config")
            .setView(wrap)
            .setNegativeButton("Annulla", null)
            .setPositiveButton("Salva") { _, _ ->
                p.edit()
                    .putString("base_url", base.text.toString().trim())
                    .putString("device_id", dev.text.toString().trim())
                    .putString("hmac_secret", secret.text.toString())
                    .apply()
                setStatus("Config salvata.")
            }
            .show()
    }

    private fun bytesToHex(bytes: ByteArray): String {
        val sb = StringBuilder(bytes.size * 2)
        for (b in bytes) sb.append(String.format("%02X", b))
        return sb.toString()
    }

    private fun randomHex(nBytes: Int): String {
        val b = ByteArray(nBytes)
        SecureRandom().nextBytes(b)
        return bytesToHex(b)
    }

    private fun hmacSha256Hex(secret: String, data: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256"))
        val out = mac.doFinal(data.toByteArray(Charsets.UTF_8))
        return bytesToHex(out).lowercase(Locale.US)
    }
}

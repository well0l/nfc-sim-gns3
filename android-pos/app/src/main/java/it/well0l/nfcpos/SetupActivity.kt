package it.well0l.nfcpos

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class SetupActivity : AppCompatActivity() {

    private fun prefs() = getSharedPreferences("nfc_portal", Context.MODE_PRIVATE)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Se URL già configurato, vai diretto al portal
        val savedUrl = prefs().getString("base_url", "")
        if (!savedUrl.isNullOrEmpty()) {
            goToPortal()
            return
        }

        setContentView(R.layout.activity_setup)

        val urlInput = findViewById<EditText>(R.id.urlInput)
        val continueButton = findViewById<Button>(R.id.continueButton)

        continueButton.setOnClickListener {
            val url = urlInput.text.toString().trim()
            if (url.isEmpty()) {
                Toast.makeText(this, "Inserisci un URL valido", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // Salva URL
            prefs().edit().putString("base_url", url).apply()

            // Vai al portal
            goToPortal()
        }
    }

    private fun goToPortal() {
        startActivity(Intent(this, PortalActivity::class.java))
        finish()
    }
}

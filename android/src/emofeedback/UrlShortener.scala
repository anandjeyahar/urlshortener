package com.emofeedback

import org.scaloid.common._
import android.graphics.Color
import scala.concurrent.future

class UrlShortener extends SActivity {

  onCreate {
    contentView = new SWebView {
      val myWebView = new SWebView()
      val mimeType: String = "text/html"
      myWebView.loadUrl("http://www.aang.in")
      this += myWebView
    }
  }
}

package com.emofeedback

import org.scaloid.common._
import android.graphics.Color
import scala.concurrent.future

class UrlShortener extends SActivity {

  onCreate {
    contentView = new SWebView {
      val myWebView = new SWebView()
      val mimeType: String = "text/html"
      myWebView.loadUrl("file:///android_res/html/index.html")
      this += myWebView
    }
  }
}

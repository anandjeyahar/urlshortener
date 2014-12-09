package urlshortener

import org.scaloid.common._
import android.graphics.Color
import scala.concurrent.future

class HelloScaloid extends SActivity {

  onCreate {
    contentView = new SVerticalLayout {
      style {
        case b: SButton => b.textColor(Color.RED).onClick(toast("Bang!"))
        case t: STextView => t textSize 10.dip
        case e: SEditText => e.backgroundColor(Color.YELLOW)
      }
      val myWebView = new SWebView()
      myWebView.loadUrl("http://aang.in")
      this += myWebView
	  this += new SLinearLayout {
	  }.wrap
    } padding 20.dip
  }
}

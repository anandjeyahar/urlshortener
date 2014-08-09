import json
import redis
import bisect
import md5
import tornado
from tornado.options import define, options
from tornado.web import RequestHandler, Application


define("debug", default=0, help="hot deployment. use in dev only", type=int)
define("port", default=8888, help="run on the given port", type=int)

REDIS_IP = "127.0.0.1"
REDIS_PORT = 6379
REPLICAS_SIZE = 10  # Number of Replicas
MIN_EXP_TIME = 24 * 60 * 60     # Expire after 1 day
REDIRECT_COUNTS_KEY = "shorturl:resolved"
HLL_KEY = "hyperloglog:original:url"
#  TODO: try using zmq  based ioloop instead might be more useful
#  TODO: add a hyperloglog based counter  of original urls
#  TODO: add that ConsistentHashRing setup to enable redis cluster

class UrlShortener(object):
    def __init__(self):
        self.redis = redis.Redis(host=REDIS_IP, port=REDIS_PORT)

    def shorten_url(self, url):
        url_exists = self.redis.pfadd(HLL_KEY_NAME, url)
        if not url_exists:
            self.short_url = long(md5.md5(url).hexdigest(), 16)
            self.redis.setex(self.short_url, url, MIN_EXP_TIME)
        else:
            self.short_url = self.redis.get(short_url)

    def retrieve_orig_url(self, short_url):
        return self.redis.get(short_url)


class ShortUrlHandler(RequestHandler):

    def get(self):
        short_url = self.get_argument("short_url")
        orig_url = url_shortener.retrieve_orig_url(short_url)
        url_shortener.redis.incrby(REDIRECT_COUNTS_KEY, 1)
        self.redirect(orig_url)

    def post(self):
        orig_url = self.get_argument("orig_url")
        url_shortener.shorten_url(orig_url)
        self.finish(json.dumps({"url": url_shortener.short_url}))

class Application(Application):
    """
        >>> import requests
        >>> requests.post("/shorten", params={"orig_url":"http://google.com"})
        >>> resp = requests.get("/shorten", params={"short_url":" 265477614567132497141480353139365708304L"})
        >>> assert resp.url=="http://google.com"
    """
    def __init__(self):
        handlers = [
                (r"/shorten", ShortUrlHandler)
                ]
        settings = dict(
            autoescape=None,  # tornado 2.1 backward compatibility
            debug=options.debug,
            gzip=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port, xheaders=True)
    loop = tornado.ioloop.IOLoop.instance()
    loop.start()

if __name__ == "__main__":
    url_shortener = UrlShortener()
    main()

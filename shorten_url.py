import json
import logging
import redis
import random
import tornado
from tornado.options import define, options
from tornado.web import RequestHandler, Application


define('debug', default=1, help='hot deployment. use in dev only', type=int)
define('port', default=8000, help='run on the given port', type=int)

REDIS_IP = '127.0.0.1'
REDIS_PORT = 6379
REPLICAS_SIZE = 10  # Number of Replicas
MIN_EXP_TIME = 24 * 60 * 60     # Expire after 1 day
REDIRECT_COUNTS_KEY = 'shorturl:resolved'
HLL_KEY = 'hyperloglog:original:url'

#  TODO: try using zmq  based ioloop instead might be more useful
#  TODO: add that ConsistentHashRing setup to enable redis cluster
#  TODO: Read up on hashing algorithms and pick best suited one for url
#  shortening service. see
#  TODO: Sanitize the incoming url, for malicious js.

class UrlShortener(object):
    # From RFC 1738 allowed url chars
    LOWALPHA       = [ 'a', 'b','c', 'd' , 'e' , 'f' , 'g' , 'h' ,
                     'i' , 'j' , 'k' , 'l' , 'm' , 'n' , 'o' , 'p' ,
                     'q' , 'r' , 's' , 't' , 'u' , 'v' , 'w' , 'x' ,
                     'y' , 'z' ]
    HIALPHA        = [ 'A' , 'B' , 'C' , 'D' , 'E' , 'F' , 'G' , 'H' ,
                     'I' , 'J' , 'K' , 'L' , 'M' , 'N' , 'O' , 'P' ,
                     'Q' , 'R' , 'S' , 'T' , 'U' , 'V' , 'W' , 'X' ,
                     'Y' , 'Z' ]
    DIGIT          = [ '0' , '1' , '2' , '3' , '4' , '5' , '6' , '7' ,
                     '8' , '9' ]
    SAFE           = [ '$' , '-' , '_' , '.' , '+' ]
    EXTRA          = [ '!' , '*' , "'" , '(' , ')' , ',' ]
    PUNCTUATION    = [ '<' , '>' , '#' , '%' , "'" ]

    URL_ALLOWED_CHARS = LOWALPHA +\
                        HIALPHA +\
                        DIGIT +\
                        SAFE +\
                        EXTRA +\
                        PUNCTUATION

    def __init__(self):
        self.redis = redis.Redis(host=REDIS_IP, port=REDIS_PORT)

    def shorten_url(self, url):
        url_not_exists = self.redis.pfadd(HLL_KEY, url)
        if url_not_exists:
            short_url = "".join([random.choice(self.URL_ALLOWED_CHARS) for i in range(5)])
            if not self.redis.get(short_url):
                self.redis.setex(short_url, url, MIN_EXP_TIME)
                self.redis.setex(url, short_url, MIN_EXP_TIME)
            else:
                # Since collisions are possible, this means there was a
                # collision
                logging.warn("#urlshortener: Collision Orig Url: %s, generated short url: %s" %(url, short_url))
                self.shorten_url(url)
        else:
            short_url = self.redis.get(url)
        return str(short_url)

    def retrieve_orig_url(self, short_url):
        return self.redis.get(short_url)



class ShortUrlHandler(RequestHandler):
    def get(self, *args):
        logging.info(args)
        if args:
            data = {"short_url": args}
            self.request.arguments = data
            self.post()
        else:
            self.render('static/index.html')

    def post(self):
        short_url = self.get_argument('short_url')
        logging.info('# Received short url: %s' % short_url)
        orig_url = url_shortener.retrieve_orig_url(short_url)
        url_shortener.redis.incrby(REDIRECT_COUNTS_KEY, 1)
        self.redirect(orig_url)

class ShortenUrlHandler(RequestHandler):
    def get(self):
        self.render('static/index.html')
    def post(self):
        orig_url = self.get_argument('orig_url')
        logging.info('# Received Original url: %s' % orig_url)
        short_url = '/'.join([self.request.headers.get('Origin'), url_shortener.shorten_url(orig_url)])
        self.finish(json.dumps({'url': short_url}))

class Application(Application):
    #  """
    #  >>> import requests
    #  >>> requests.post("/shorten", params={"orig_url":"http://google.com"})
    #  >>> resp = requests.get("/shorten", params={"short_url": "265477614567132497141480353139365708304L"})
    #  >>> assert resp.url=="http://google.com"
    #  """
    def __init__(self):
        handlers = [
                (r'/shorten', ShortenUrlHandler),
                (r'/(?!shorten|.*^)', ShortUrlHandler),
                ]
        settings = dict(
            autoescape=None,  # tornado 2.1 backward compatibility
            debug=options.debug,
            gzip=True,
            )
        settings.update({'static_path':'./static'})
        tornado.web.Application.__init__(self, handlers, **settings)

def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port, xheaders=True)
    loop = tornado.ioloop.IOLoop.instance()
    loop.start()
if __name__ == '__main__':
    url_shortener = UrlShortener()
    main()

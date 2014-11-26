import json
import logging
import os
import random
import redis
import sys
import tornado
import urllib
from tornado.options import define, options
from tornado.web import RequestHandler, Application

define('debug', default=1, help='hot deployment. use in dev only', type=int)
define('port', default=8000, help='run on the given port', type=int)

MIN_EXP_TIME = 30 * 24 * 60 * 60     # Expire after 30 days

REDIRECT_COUNTS_KEY = 'url:shorturl:resolved'
HLL_ORIG_URL_KEY = 'url:hyperloglog:original'

DOMAIN_REGEX = '[a-zA-Z\d-]{,63}(\.[a-zA-Z\d-]{,63})*'
SHORT_URL_KEY = 'short:url:'
ORIG_URL_KEY = 'orig:url:'

redistogo_url = os.getenv('REDISTOGOURL')
if redistogo_url:
    #redis_url = redistogo_url.split('redis://redistogo:')[1]
    #redis_url = redis_url.split('/')[0]
    redisToGoConn = redis.from_url(redistogo_url)
#  TODO: try using zmq  based ioloop instead might be more useful
#  TODO: add that ConsistentHashRing setup to enable redis cluster
#  TODO: Read up on hashing algorithms and pick best suited one for url
#  shortening service. see
def validate_safe_url(url):
    #  TODO: Sanitize the incoming url, for malicious js.
    # Check if it's already a shortened url
    if redisToGoConn.get(SHORT_URL_KEY + url):
        return False
    return  True
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
        self.redis = redisToGoConn

    def get_stats(self):
        urls_count = self.redis.pfcount(HLL_ORIG_URL_KEY) if self.redis.pfcount(HLL_ORIG_URL_KEY) else 0
        redirects = self.redis.get(REDIRECT_COUNTS_KEY) if self.redis.get(REDIRECT_COUNTS_KEY) else 0
        stats = {r'urls':urls_count,
                 r'redirects':redirects
                 }
        return stats

    def shorten_url(self, url):
        safe_url = validate_safe_url(url)
        # Check if the given url is a shortened url. stop malicious programs from inducing a redirect loop
        if not safe_url:
            logging.warn("#urlshortener: short_url provided as input for shortening")
            return None
        orig_url_not_exists = self.redis.pfadd(HLL_ORIG_URL_KEY, url)
        if orig_url_not_exists:
            short_url = "".join([random.choice(self.URL_ALLOWED_CHARS) for i in range(5)])
            if not self.redis.get(SHORT_URL_KEY + short_url):
                self.redis.setex(SHORT_URL_KEY + short_url, url, MIN_EXP_TIME)
                self.redis.setex(ORIG_URL_KEY + url, short_url, MIN_EXP_TIME)
            else:
                # Since collisions are possible, this means there was a
                # collision
                logging.warn("#urlshortener: Collision Orig Url: %s, generated short url: %s" %(url, short_url))
                self.shorten_url(url)
        else:
            # Original url already shortenede, just return th
            short_url = self.redis.get(ORIG_URL_KEY + url)
        return short_url

    def retrieve_orig_url(self, short_url):
        return str(self.redis.get(SHORT_URL_KEY + short_url))

class ShortUrlHandler(RequestHandler):
    def get(self):
        self.post()

    def post(self):
        url_parts = self.request.uri.split('/')
        short_url = urllib.unquote_plus(url_parts[1]) if len(url_parts) > 1 else None
        if short_url:
            logging.info('# Received short url: %s' % short_url)
            orig_url = url_shortener.retrieve_orig_url(short_url)
            url_shortener.redis.incrby(REDIRECT_COUNTS_KEY, 1)
            assert orig_url, logging.warn('short url doesnot have an entry in hash tabel, but is present in HLL')
            self.redirect(orig_url)
        else:
            self.redirect('/shorten')

class ShortenUrlHandler(RequestHandler):
    def get(self):
        self.render('static/index.html')
    def post(self):
        orig_url = self.get_argument('orig_url')
        logging.info('# Received url: %s' % orig_url)
        import pdb; pdb.set_trace()
        short_url = url_shortener.shorten_url(orig_url)
        if short_url:
            linkified_short_url = '<a href=' + '/'.join([self.request.headers.get('Origin'),
                                                         urllib.quote_plus(short_url)]) + '>Click Here</a>'
            self.finish(json.dumps({'url': linkified_short_url}, ensure_ascii=False).encode('utf-8'))

class StatsHandler(RequestHandler):
    def get(self):
        self.finish(json.dumps(url_shortener.get_stats(), ensure_ascii=False).encode('utf-8'))

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
                (r'/stats',StatsHandler),
                (r'/(?!stats|shorten).*', ShortUrlHandler),
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

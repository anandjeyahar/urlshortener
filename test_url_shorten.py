import requests
import json

def test_shorten_new_url():
    orig_url = "http://google.com"
    resp = requests.post("http://localhost:8888/shorten", params={"orig_url":orig_url})
    url = json.loads(resp.text).get("url")
    resp = requests.post("http://localhost:8888", params={"short_url": url})
    assert (resp.url.find("google") > 0)


def main():
    test_shorten_new_url()

if __name__ == "__main__":
    main()

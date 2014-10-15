import base64
import mimetypes
import urllib

# based on https://gist.github.com/panzi/4004353

def parse(url):
    return DataUrl(url)

class DataUrl(object):
    def __init__(self, url):
        self.url = url
        scheme, data = url.split(':', 1)
        assert scheme == 'data', 'Unsupported URL scheme: ' + scheme

        media_type, data = data.split(',', 1)
        media_type = media_type.split(';')
        self.data = urllib.unquote(data)
        self.is_base64 = False

        self.mime_type = media_type[0]
        for t in media_type[1:]:
            if t == 'base64':
                self.is_base64 = True
            # TODO: Handle charset= parameter?

        if self.is_base64:
            self.data = base64.b64decode(self.data)

        self.extension = mimetypes.guess_extension(self.mime_type)

import datetime
import feedparser

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from bs4 import BeautifulSoup

ua = 'Django-aggregator/dev +http://github.com/brutasse/django-aggregator'
feedparser.USER_AGENT = ua


class Feed(models.Model):
    title = models.CharField(_('Title'), max_length=500)
    feed_url = models.URLField(_('Feed URL'), unique=True, max_length=500)
    public_url = models.URLField(_('Public URL'), max_length=500)
    is_defunct = models.BooleanField(_('Is defunct'))

    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return u'%s' % self.title

    def update(self):
        parsed = feedparser.parse(self.feed_url)
        try:
            encoding = settings.AGGREGATOR_ENCODING
        except AttributeError:
            encoding = parsed.encoding

        for entry in parsed.entries:
            title = entry.title.encode(encoding, "xmlcharrefreplace")
            guid = entry.get('id', entry.link).encode(encoding,
                                                      "xmlcharrefreplace")
            link = entry.link.encode(encoding, "xmlcharrefreplace")
            image = None

            if not guid:
                guid = link

            if 'summary' in entry:
                summary = entry.summary
            elif 'description' in entry:
                summary = entry.description
            else:
                summary = u''

            summary = summary.encode(encoding, "xmlcharrefreplace")

            if 'content' in entry:
                content = entry.content[0].value
            else:
                content = u''

            for entry_link in entry.links:
                if 'image' in entry_link.type:
                    image = entry_link.href
            if image is None:
                image = self.parse_image(content)

            content = content.encode(encoding, "xmlcharrefreplace")

            if 'updated_parsed' in entry and entry.updated_parsed is not None:
                date_modified = datetime.datetime(*entry.updated_parsed[:6])
            else:
                date_modified = datetime.datetime.utcnow()

            try:
                self.entries.get(guid=guid)
            except Entry.DoesNotExist:
                self.entries.create(title=title, link=link, summary=summary,
                content=content, guid=guid, date=date_modified, image=image)


    def parse_image(self, content):
        soup = BeautifulSoup(content)
        img = soup.img
        if img is None:
            return None

        if 'height' in img and 'width' in img:
            height = int(img['height'])
            width = int(img['width'])

            if height < 100 or width < 100:
                return None

        image = img['src']

        rejected_images = [
            'wp-includes/images/smilies',
            'flattr-badge',
            "'+uri +'"
        ]

        for rejected in rejected_images:
            if rejected in image:
                return None

        return image


class Entry(models.Model):
    feed = models.ForeignKey(Feed, verbose_name=_('Feed'),
                             related_name='entries')
    title = models.CharField(_('Title'), max_length=500)
    link = models.URLField(_('Link'), max_length=500)
    content = models.TextField(_('Content'))
    summary = models.TextField(_('Summary'), blank=True)
    date = models.DateTimeField(_('Date'))
    guid = models.CharField(_('GUID'), max_length=500,
                            unique=True, db_index=True)
    image = models.URLField(_('Image'), max_length=500, blank=True, null=True)

    class Meta:
        ordering = ('-date',)
        verbose_name_plural = _('Entries')

    def __unicode__(self):
        return u'%s' % self.title

    def get_absolute_url(self):
        return self.link

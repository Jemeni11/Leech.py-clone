#!/usr/bin/python

import logging
import itertools
import datetime
import re
from . import register, Site, Section, Chapter

logger = logging.getLogger(__name__)


@register
class FictionLive(Site):
    """fiction.live: it's... mostly smut, I think? Terrible smut. But, hey, I had a rec to follow."""
    @staticmethod
    def matches(url):
        # e.g. https://fiction.live/stories/Descendant-of-a-Demon-Lord/SBBA49fQavNQMWxFT
        match = re.match(r'^(https?://fiction\.live/(?:stories|Sci-fi)/[^\/]+/[0-9a-zA-Z\-]+)/?.*', url)
        if match:
            return match.group(1)

    def extract(self, url):
        workid = re.match(r'^https?://fiction\.live/(?:stories|Sci-fi)/[^\/]+/([0-9a-zA-Z\-]+)/?.*', url).group(1)

        response = self.session.get(f'https://fiction.live/api/node/{workid}').json()

        story = Section(
            title=response['t'],
            author=response['u'][0]['n'],
            # Could normalize the URL here from the returns, but I'd have to
            # go look up how they handle special characters in titles...
            url=url
        )
        # There's a summary (or similar) in `d` and `b`, if I want to use that later.

        # TODO: extract these #special ones and send them off to an endnotes section?
        chapters = ({'ct': 0},) + tuple(c for c in response['bm'] if not c['title'].startswith('#special')) + ({'ct': 9999999999999999},)

        for prevc, currc, nextc in contextiterate(chapters):
            # `id`, `title`, `ct`, `isFirst`
            # https://fiction.live/api/anonkun/chapters/SBBA49fQavNQMWxFT/0/1448245168594
            # https://fiction.live/api/anonkun/chapters/SBBA49fQavNQMWxFT/1449266444062/1449615394752
            # https://fiction.live/api/anonkun/chapters/SBBA49fQavNQMWxFT/1502823848216/9999999999999998
            # i.e. format is [current timestamp] / [next timestamp - 1]
            chapter_url = f'https://fiction.live/api/anonkun/chapters/{workid}/{currc["ct"]}/{nextc["ct"] - 1}'
            logger.info("Extracting chapter \"%s\" @ %s", currc['title'], chapter_url)
            data = self.session.get(chapter_url).json()
            html = []

            updated = currc['ct']
            for segment in (d for d in data if not d.get('t', '').startswith('#special')):
                updated = max(updated, segment['ct'])
                # TODO: work out if this is actually enough types handled
                # There's at least also a reader post type, which mostly seems to be used for die rolls.
                try:
                    if segment['nt'] == 'chapter':
                        html.extend(('<div>', segment['b'].replace('<br>', '<br/>'), '</div>'))
                    elif segment['nt'] == 'choice':
                        if 'votes' not in segment:
                            # Somehow, sometime, we end up with a choice without votes (or choices)
                            continue
                        votes = {}
                        for vote in segment['votes']:
                            votechoices = segment['votes'][vote]
                            if type(votechoices) == str:
                                # This caused issue #30, where for some reason one
                                # choice on a story was a string rather than an
                                # index into the choices array.
                                continue
                            if type(votechoices) == int:
                                votechoices = (votechoices,)
                            for choice in votechoices:
                                if int(choice) < len(segment['choices']):
                                    # sometimes someone has voted for a presumably-deleted choice
                                    choice = segment['choices'][int(choice)]
                                    votes[choice] = votes.get(choice, 0) + 1
                        choices = [(votes[v], v) for v in votes]
                        choices.sort(reverse=True)

                        closed = "closed" if 'closed' in segment.keys() else "open"
                        vote_title = segment['b'] if 'b' in segment.keys() else "Choices"

                        vote_header_output = f"<h3 class='vote_header_output center'>{vote_title} — <small>Voting {closed} </small></h3>"

                        html.append(f'{vote_header_output}<hr/><ul class="votes_ul_list">')
                        for votecount, choice in choices:
                            html.append(f'<li><span class="li_left">{choice}</span> <span class="li_right">{votecount}</span></li>')
                        html.append('</ul><hr/>')
                    elif segment['nt'] == 'readerPost':
                        reader_post_title = segment['b'] if 'b' in segment.keys() else "Reader Post"
                        closed = "closed" if 'closed' in segment.keys() else "open"
                        for i in ["dice", "votes"]:
                            if i in segment.keys():
                                if i == "dice":
                                    dice_title = '<h3 class="reader_post_title center">'
                                    if reader_post_title == "Reader Post":
                                        dice_title += '<span>Dice</span></h3>'
                                    else:
                                        dice_title += f'<span<Dice: {reader_post_title}</span></h3>'
                                    html.append(dice_title)
                                elif i == "votes":
                                    html.append(
                                        f'<h3 class="reader_post_title center">'
                                        f'<span>{reader_post_title}</span> - '
                                        f'<small>Posting {closed} </small></h3>')
                                html.append('<hr/><ul class="reader_post_list">')
                                for j in segment[i]:
                                    html.append(f'<li>{segment[i][j]}</li>')
                                html.append('</ul><hr/>')
                    else:
                        logger.info("Skipped chapter-segment of unhandled type: %s", segment['nt'])
                except Exception as e:
                    logger.error("Skipped chapter-segment due to parsing error", exc_info=e)

            story.add(Chapter(
                title=currc['title'],
                contents='\n'.join(html),
                date=datetime.datetime.fromtimestamp(updated / 1000.0)
            ))

        return story


# Stolen from the itertools docs
def contextiterate(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b, c = itertools.tee(iterable, 3)
    next(b, None)
    next(c, None)
    next(c, None)
    return zip(a, b, c)

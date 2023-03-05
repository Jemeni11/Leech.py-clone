from .epub import make_epub, EpubFile
from .cover import make_cover, make_cover_from_url
from .image import get_image_from_url
from bs4 import BeautifulSoup
from sites import Image
import html
import unicodedata
import datetime
import attr

html_template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="../Styles/base.css" />
</head>
<body>
<h1>{title}</h1>
{text}
</body>
</html>
'''

cover_template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Cover</title>
    <link rel="stylesheet" type="text/css" href="Styles/base.css" />
</head>
<body>
<div class="cover">
<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
    width="100%" height="100%" viewBox="0 0 573 800" preserveAspectRatio="xMidYMid meet">
<image width="600" height="800" xlink:href="images/cover.png" />
</svg>
</div>
</body>
</html>
'''

frontmatter_template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Front Matter</title>
    <link rel="stylesheet" type="text/css" href="Styles/base.css" />
</head>
<body>
<div class="cover title">
    <h1>{title}<br />By {author}</h1>
    <dl>
        <dt>Source</dt>
        <dd>{unique_id}</dd>
        <dt>Started</dt>
        <dd>{started:%Y-%m-%d}</dd>
        <dt>Updated</dt>
        <dd>{updated:%Y-%m-%d}</dd>
        <dt>Downloaded on</dt>
        <dd>{now:%Y-%m-%d}</dd>
        {extra}
    </dl>
</div>
</body>
</html>
'''

css_styles = """
    /* This assumes geometric header shrinkage */
/* Also, it tries to make h2 be 1em */
html, body, div, span, applet, object, iframe, h1, h2, h3, h4, h5, h6, p, blockquote, pre, a, abbr, acronym, address, big, cite, code, del, dfn, em, img, ins, kbd, q, s, samp, small, strike, strong, sub, sup, tt, var, b, u, i, center, dl, dt, dd, fieldset, form, label, legend, table, caption, tbody, tfoot, thead, tr, th, td, article, aside, canvas, details, embed, figure, figcaption, footer, header, hgroup, menu, nav, output, ruby, section, summary, time, mark, audio, video {
  /* Note kindle hates margin:0 ! (or margin-left or margin-top set) it inserts newlines galore */
  /* margin: 0 */
  margin-right: 0;
  padding: 0;
  border: 0;
  font-size: 100%;
  /* font: inherit */
  vertical-align: baseline; }

/* optimal sizing see http://demosthenes.info/blog/578/Crafting-Optimal-Type-Sizes-For-Web-Pages */
/* kobo and nook dislike this */
/* */
/*html */
/*  font-size: 62.5% */
/*body */
/*  font-size: 1.6rem */
/*  line-height: 2.56rem */
/*  text-rendering: optimizeLegibility */
table {
  border-collapse: collapse;
  border-spacing: 0; }

/* end reset */
@page {
  margin-top: 30px;
  margin-bottom: 20px; }

div.cover {
  text-align: center;
  page-break-after: always;
  padding: 0px;
  margin: 0px; }
  div.cover img {
    height: 100%;
    max-width: 100%;
    padding: 10px;
    margin: 0px;
    background-color: #cccccc; }

.half {
  max-width: 50%; }

.tenth {
  max-width: 10%;
  width: 10%; }

.cover-img {
  height: 100%;
  max-width: 100%;
  padding: 0px;
  margin: 0px; }

/* font plan- serif text, sans headers */
h1, h2, h3, h4, h5, h6 {
  hyphens: none !important;
  -moz-hyphens: none !important;
  -webkit-hyphens: none !important;
  adobe-hyphenate: none !important;
  page-break-after: avoid;
  page-break-inside: avoid;
  text-indent: 0px;
  text-align: left;
  font-family: Helvetica, Arial, sans-serif; }

h1 {
  font-size: 1.6em;
  margin-bottom: 3.2em; }

.title h1 {
  margin-bottom: 0px;
  margin-top: 3.2em; }

h2 {
  font-size: 1em;
  margin-top: 0.5em;
  margin-bottom: 0.5em; }

h3 {
  font-size: 0.625em; }

h4 {
  font-size: 0.391em; }

h5 {
  font-size: 0.244em; }

h6 {
  font-size: 0.153em; }

/* Do not indent first paragraph. Mobi will need class='first-para' */
h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p {
  text-indent: 0; }

p {
  /* paperwhite defaults to sans */
  font-family: "Palatino", "Times New Roman", Caecilia, serif;
  -webkit-hyphens: auto;
  -moz-hyphens: auto;
  hyphens: auto;
  hyphenate-after: 3;
  hyphenate-before: 3;
  hyphenate-lines: 2;
  -webkit-hyphenate-after: 3;
  -webkit-hyphenate-before: 3;
  -webkit-hyphenate-lines: 2;
  line-height: 1.5em;
  margin: 0;
  text-align: justify;
  text-indent: 1em;
  orphans: 2;
  widows: 2; }
  p.first-para, p.first-para-chapter, p.note-p-first {
    text-indent: 0; }
  p.first-para-chapter::first-line {
    /* handle run-in */
    font-variant: small-caps; }
  p.no-indent {
    text-indent: 0; }

.no-hyphens {
  hyphens: none !important;
  -moz-hyphens: none !important;
  -webkit-hyphens: none !important;
  adobe-hyphenate: none !important; }

.rtl {
  direction: rtl;
  float: right; }

.drop {
  overflow: hidden;
  line-height: 89%;
  height: 0.8em;
  font-size: 281%;
  margin-right: 0.075em;
  float: left; }

.dropcap {
  line-height: 100%;
  font-size: 341%;
  margin-right: 0.075em;
  margin-top: -0.22em;
  float: left;
  height: 0.8em; }

.vote_header_output,
.reader_post_title {
    font-size: 1em;
}

hr {
  margin-top: 1em;
  margin-bottom: 1em;
}

/* lists */
ul, ol, dl {
  margin: 1em 0 1em 0;
  text-align: left; }

ul.votes_ul_list,
ul.reader_post_list {
    list-style-type: none;
    box-sizing: border-box;
    padding-inline: 1rem;
}

ul.votes_ul_list li,
ul.reader_post_list li {
    display: flex;
    margin-bottom: 0.5em;
}

ul.votes_ul_list li span.li_left {
    width: 80%;
    text-align: left;
}

ul.votes_ul_list li span.li_right {
    width: 20%;
    text-align: right;
}

li {
  font-family: "Palatino", "Times New Roman", Caecilia, serif;
  line-height: 1.5em;
  orphans: 2;
  widows: 2;
  text-align: justify;
  text-indent: 0;
  margin: 0;
}
  li p {
    /* Fix paragraph indenting inside of lists */
    text-indent: 0em; }

dt {
  font-weight: bold;
  font-family: Helvetica, Arial, sans-serif; }

dd {
  line-height: 1.5em;
  font-family: "Palatino", "Times New Roman", Caecilia, serif; }
  dd p {
    /* Fix paragraph indenting inside of definition lists */
    text-indent: 0em; }

blockquote {
  margin-left: 1em;
  margin-right: 1em;
  line-height: 1.5em;
  font-style: italic; }
  blockquote p.first-para, blockquote p {
    text-indent: 0; }

pre, tt, code, samp, kbd {
  font-family: "Courier New", Courier, monospace;
  word-wrap: break-word; }

pre {
  font-size: 0.8em;
  line-height: 1.2em;
  margin-left: 1em;
  /* margin-top: 1em */
  margin-bottom: 1em;
  white-space: pre-wrap;
  display: block; }

img {
  border-radius: 0;
  -webkit-border-radius: 0;
  box-sizing: border-box;
  border: none;
  /* Don't go too big on images, let reader zoom in if they care to */
  max-width: 90%;
  max-height: 90%; }

img .img_center {
  text-indent: 0;
  text-align: center;
  margin: 1em auto;
  display: block;
}

img.pwhack {
  /* Paperwhite hack */
  width: 100%; }

.group {
  page-break-inside: avoid; }

.caption {
  text-align: center;
  font-size: 0.8em;
  font-weight: bold; }

p img {
  border-radius: 0;
  border: none; }

figure {
  /* These first 3 should center figures */
  text-align: center; }
  figure figcaption {
    text-align: center;
    font-size: 0.8em;
    font-weight: bold; }

div.div-literal-block-admonition {
  margin-left: 1em;
  background-color: #cccccc; }
div.note, div.tip, div.hint {
  margin: 1em 0 1em 0 !important;
  background-color: #cccccc;
  padding: 1em !important;
  /* kindle is finnicky with borders, bottoms dissappear, width is ignored */
  border-top: 0px solid #cccccc;
  border-bottom: 0px dashed #cccccc;
  page-break-inside: avoid; }

/* sidebar */
p.note-title, .admonition-title {
  margin-top: 0;
  /*mobi doesn't like div margins */
  font-variant: small-caps;
  font-size: 0.9em;
  text-align: center;
  font-weight: bold;
  font-style: normal;
  -webkit-hyphens: none;
  -moz-hyphens: none;
  hyphens: none;
  /* margin:0 1em 0 1em */ }

div.note p, .note-p {
  text-indent: 1em;
  margin-left: 0;
  margin-right: 0; }

/*  font-style: italic */
/* Since Kindle doesn't like multiple classes have to have combinations */
div.note p.note-p-first {
  text-indent: 0;
  margin-left: 0;
  margin-right: 0; }

/* Tables */
table {
  /*width: 100% */
  page-break-inside: avoid;
  border: 1px;
  /* centers on kf8 */
  margin: 1em auto;
  border-collapse: collapse;
  border-spacing: 0; }

th {
  font-variant: small-caps;
  padding: 5px !important;
  vertical-align: baseline;
  border-bottom: 1px solid black; }

td {
  font-family: "Palatino", "Times New Roman", Caecilia, serif;
  font-size: small;
  hyphens: none;
  -moz-hyphens: none;
  -webkit-hyphens: none;
  padding: 5px !important;
  page-break-inside: avoid;
  text-align: left;
  text-indent: 0;
  vertical-align: baseline; }

td:nth-last-child {
  border-bottom: 1px solid black; }

.zebra {
  /* shade background by groups of three */ }
  .zebra tr th {
    background-color: white; }
  .zebra tr:nth-child(6n-1), .zebra tr:nth-child(6n+0), .zebra tr:nth-child(6n+1) {
    background-color: #cccccc; }

sup {
  vertical-align: super;
  font-size: 0.5em;
  line-height: 0.5em; }

sub {
  vertical-align: sub;
  font-size: 0.5em;
  line-height: 0.5em; }

table.footnote {
  margin: 0.5em 0em 0em 0em; }

.footnote {
  font-size: 0.8em; }

.footnote-link {
  font-size: 0.8em;
  vertical-align: super; }

.tocEntry-1 a {
  /* empty */
  font-weight: bold;
  text-decoration: none;
  color: black; }

.tocEntry-2 a {
  margin-left: 1em;
  text-indent: 1em;
  text-decoration: none;
  color: black; }

.tocEntry-3 a {
  text-indent: 2em;
  text-decoration: none;
  color: black; }

.tocEntry-4 a {
  text-indent: 3em;
  text-decoration: none;
  color: black; }

.copyright-top {
  margin-top: 6em; }

.page-break-before {
  page-break-before: always; }

.page-break-after {
  page-break-after: always; }

.center {
  text-indent: 0;
  text-align: center;
  margin-left: auto;
  margin-right: auto;
  display: block; }

.right {
  text-align: right; }

.left {
  text-align: left; }

.f-right {
  float: right; }

.f-left {
  float: left; }

/* Samples */
.ingredient {
  page-break-inside: avoid; }

.box-example {
  background-color: #8ae234;
  margin: 2em;
  padding: 1em;
  border: 2px dashed #ef2929; }

.blue {
  background-color: blue; }

.dashed {
  border: 2px dashed #ef2929; }

.padding-only {
  padding: 1em; }

.margin-only {
  margin: 2em; }

.smaller {
  font-size: 0.8em; }

.em1 {
  font-size: 0.5em; }

.em2 {
  font-size: 0.75em; }

.em3 {
  font-size: 1em; }

.em4 {
  font-size: 1.5em; }

.em5 {
  font-size: 2em; }

.per1 {
  font-size: 50%; }

.per2 {
  font-size: 75%; }

.per3 {
  font-size: 100%; }

.per4 {
  font-size: 150%; }

.per5 {
  font-size: 200%; }

.mousepoem p {
  line-height: 0;
  margin-left: 1em; }

.per100 {
  font-size: 100%;
  line-height: 0.9em; }

.per90 {
  font-size: 90%;
  line-height: 0.9em; }

.per80 {
  font-size: 80%;
  line-height: 0.9em; }

.per70 {
  font-size: 70%;
  line-height: 0.9em; }

.per60 {
  font-size: 60%;
  line-height: 0.9em; }

.per50 {
  font-size: 50%;
  line-height: 1.05em; }

.per40 {
  font-size: 40%;
  line-height: 0.9em; }

.size1 {
  font-size: x-small; }

.size2 {
  font-size: small; }

.size3 {
  /* default */
  font-size: medium; }

.size4 {
  font-size: large; }

.size5 {
  font-size: x-large; }

/* Poetic margins */
.stanza {
  margin-top: 1em;
  font-family: serif;
  padding-left: 1em; }
  .stanza p {
    padding-left: 1em; }

.poetry {
  margin: 1em; }

/*line number */
.ln {
  float: left;
  color: #999999;
  font-size: 0.8em;
  font-style: italic; }

.pos1 {
  margin-left: 1em;
  text-indent: -1em; }

.pos2 {
  margin-left: 2em;
  text-indent: -1em; }

.pos3 {
  margin-left: 3em;
  text-indent: -1em; }

.pos4 {
  margin-left: 4em;
  text-indent: -1em; }

@font-face {
  font-family: Inconsolata Mono;
  font-style: normal;
  font-weight: normal;
  src: url("Inconsolata.otf"); }

.normal-mono {
  font-family: "Courier New", Courier, monospace; }

tt, pre, .mono {
  /* Kindle Keyboard has KF8 but no font support, fallback to default mono */
  font-family: "Inconsolata Mono", "Courier New", Courier, monospace;
  font-style: normal; }

@font-face {
  font-family: mgopen modata;
  font-style: normal;
  font-weight: normal;
  font-size: 0.5em;
  src: url("MgOpenModataRegular.ttf"); }

.modata {
  font-family: "mgopen modata"; }

@font-face {
  font-family: hidden;
  font-style: normal;
  font-weight: normal;
  font-size: 1em;
  src: url("invisible1.ttf"); }

.hidden-font {
  font-family: "hidden"; }

/* Nook works to here :) */
/* media queries at bottom to not confuse other platforms */
@media (min-width: 200px) {
  .px200 {
    color: #8ae234; } }
@media (min-width: 400px) {
  .px400 {
    color: #8ae234; } }
@media (min-width: 800px) {
  .px800 {
    color: #8ae234; } }
@media (min-width: 1200px) {
  .px1200 {
    color: #8ae234; } }
/* broke nook! */
/*/* WIP device specific... */
/*@media (min-width: 600px) and (height: 800px) and (amzn-kf8) */
/*  /* Kindle Keyboard w/ KF8 */
/*  .kk */
/*    color: $green */
/* */
/*/* @media (min-width: 768px) and (height: 1024px) and (amzn-kf8) */
/*@media (min-width: 748px) and (min-height: 1004px) and (amzn-kf8) */
/*  /* Kindle Paperwhite */
/*  .kpw */
/*    color: $green */
/* */
/*@media (width: 600px) and (height: 1024px) and (amzn-kf8) */
/*  /* Kindle Fire */
/*  .kf */
/*    color: $green */
/* */
/*/* Retina iPad */
/*@media (-webkit-min-device-pixel-ratio: 1.5), (min-device-pixel-ratio: 1.5) */
/*  .retina */
/*    color: $green */
/* */
@media amzn-kf8 {
  span.dropcapold {
    font-size: 300%;
    font-weight: bold;
    height: 1em;
    float: left;
    margin: -0.2em 0.1em 0 0.1em; }

  .dropcap {
    line-height: 100%;
    font-size: 341%;
    margin-right: 0.075em;
    margin-top: -0.22em;
    float: left;
    height: 0.8em; } }
@media amzn-mobi {
  span.dropcap {
    font-size: 1.5em;
    font-weight: bold; }

  /*  tt, pre */
  /*    font-size: 3 */
  /*     Size table */
  /* name     becomes */
  /* x-small  2 */
  /* small    3 */
  /* medium   4 */
  /*     1em  default (nothing) */
  tt {
    /* mobi fun */
    /* font-size: x-small  /* turns into <font size="2" */
    font-family: "Courier New", Courier, monospace; }

  pre {
    margin-left: 1em;
    margin-bottom: 1em;
    /* mobi fun */
    font-size: x-small;
    font-family: "Courier New", Courier, monospace;
    white-space: pre-wrap;
    display: block; }
    pre .no-indent {
      margin-left: 0em;
      text-indent: 0em; }

  div.no-indent {
    margin-left: 0em;
    text-indent: 0em; }

  /* Sass wants to add em to the end..., hardcoded for now */
  h1 {
    font-size: 2em; }

  h2 {
    font-size: 1em; }

  h3 {
    font-size: 2em; }

  h4 {
    font-size: 1em; }

  blockquote {
    /* something in this css causes blockquotes to get doubly indented! (BUG) */
    font-style: italics;
    margin-left: 0em;
    margin-right: 0em; }

  /* descendant selectors don't work in mobi7 infact this will override the preview h1 defintion! */
  /* h1 tt, h2 tt { */
  /*   font-size: 1em; */
  /*   color: green;} */
  div.note {
    border: 1px solid black;
    /*text-indent: 1em */ }

  div.note, .note-p {
    text-indent: 1em;
    margin-left: 0;
    margin-right: 0;
    font-style: italic; }

  /* Since Kindle doesn't like multiple classes have to have combinations (fixed in 2.7) */
  .note-p-first {
    text-indent: 0;
    margin-left: 1em;
    margin-right: 1em; }

  .note-p {
    text-indent: 1em;
    margin-left: 1em;
    margin-right: 1em; }

  /* Poetry handing indent hacks */
  /* see http://ebookarchitects.com/blog/backwards-compatible-poetry-for-kf8mobi/ */
  /* and http://www.pigsgourdsandwikis.com/2012/01/media-queries-for-formatting-poetry-on.html */
  .pos1 {
    text-indent: -1em; }

  .pos2 {
    text-indent: -1em; }

  .pos3 {
    text-indent: -1em; }

  .pos4 {
    text-indent: -1em; } }
/* does nook ignore this? */
.green {
  color: #8ae234; }

/*These break NOOK! */
/*@media (monochrome) */
/*  .monochrome */
/*    color: $green */
/* */
/*@media (color) */
/*  .color */
/*    color: $green */
/* */
"""

@attr.s
class CoverOptions:
    fontname = attr.ib(default=None, converter=attr.converters.optional(str))
    fontsize = attr.ib(default=None, converter=attr.converters.optional(int))
    width = attr.ib(default=None, converter=attr.converters.optional(int))
    height = attr.ib(default=None, converter=attr.converters.optional(int))
    wrapat = attr.ib(default=None, converter=attr.converters.optional(int))
    bgcolor = attr.ib(default=None, converter=attr.converters.optional(tuple))
    textcolor = attr.ib(
        default=None, converter=attr.converters.optional(tuple))
    cover_url = attr.ib(default=None, converter=attr.converters.optional(str))


def chapter_html(story, titleprefix=None, normalize=False):
    chapters = []
    for i, chapter in enumerate(story):
        title = chapter.title or f'#{i}'
        if hasattr(chapter, '__iter__'):
            # This is a Section
            chapters.extend(chapter_html(
                chapter, titleprefix=title, normalize=normalize))
        else:
            soup = BeautifulSoup(chapter.contents, 'html5lib')
            all_images = soup.find_all('img')
            len_of_all_images = len(all_images)
            print(f"\nFound {len_of_all_images} images in chapter {i}\n")

            for count, img in enumerate(all_images):
                if not img.has_attr('src'):
                    print(f"Image {count+1} has no src attribute, skipping...")
                    continue
                print(f"Downloading image {count+1} out of {len_of_all_images} from chapter {i}")
                coverted_image_bytes, ext, mime = get_image_from_url(img['src'])
                chapter.images.append(Image(
                    path=f"images/ch{i}_leechimage_{count}.{ext}",
                    contents=coverted_image_bytes,
                    content_type=mime
                ))
                img['src'] = f"../images/ch{i}_leechimage_{count}.{ext}"
                if not img.has_attr('alt'):
                    img['alt'] = f"Image {count} from chapter {i}"
                if img.has_attr('class'):
                    img['class'] += " img_center"
                else:
                    img['class'] = "img_center"
            # Add all pictures on this chapter as well.
            for chapter_image in chapter.images:
                # For/else syntax, check if the image path already exists, if it doesn't add the image.
                # Duplicates are not allowed in the format.
                for other_file in chapters:
                    if other_file.path == chapter_image.path:
                        break
                else:
                    chapters.append(EpubFile(
                        path=chapter_image.path, contents=chapter_image.contents, filetype=chapter_image.content_type))

            title = titleprefix and f'{titleprefix}: {title}' or title
            contents = str(soup)
            if normalize:
                title = unicodedata.normalize('NFKC', title)
                contents = unicodedata.normalize('NFKC', contents)
            chapters.append(EpubFile(
                title=title,
                path=f'{story.id}/chapter{i + 1}.html',
                contents=html_template.format(
                    title=html.escape(title), text=contents)
            ))
    if story.footnotes:
        chapters.append(EpubFile(title="Footnotes", path=f'{story.id}/footnotes.html', contents=html_template.format(
            title="Footnotes", text='\n\n'.join(story.footnotes))))
    return chapters


def generate_epub(story, cover_options={}, output_filename=None, output_dir=None, normalize=False):
    dates = list(story.dates())
    metadata = {
        'title': story.title,
        'author': story.author,
        'unique_id': story.url,
        'started': min(dates),
        'updated': max(dates),
        'extra': '',
    }
    extra_metadata = {}

    if story.summary:
        extra_metadata['Summary'] = story.summary
    if story.tags:
        extra_metadata['Tags'] = ', '.join(story.tags)

    if extra_metadata:
        metadata['extra'] = '\n        '.join(
            f'<dt>{k}</dt><dd>{v}</dd>' for k, v in extra_metadata.items())

    valid_cover_options = ('fontname', 'fontsize', 'width',
                           'height', 'wrapat', 'bgcolor', 'textcolor', 'cover_url')
    cover_options = CoverOptions(
        **{k: v for k, v in cover_options.items() if k in valid_cover_options})
    cover_options = attr.asdict(
        cover_options, filter=lambda k, v: v is not None, retain_collection_types=True)

    if cover_options and "cover_url" in cover_options:
        image = make_cover_from_url(
            cover_options["cover_url"], story.title, story.author)
    elif story.cover_url:
        image = make_cover_from_url(story.cover_url, story.title, story.author)
    else:
        image = make_cover(story.title, story.author, **cover_options)

    return make_epub(
        output_filename or story.title + '.epub',
        [
            # The cover is static, and the only change comes from the image which we generate
            EpubFile(title='Cover', path='cover.html', contents=cover_template),
            EpubFile(title='Front Matter', path='frontmatter.html', contents=frontmatter_template.format(
                now=datetime.datetime.now(), **metadata)),
            *chapter_html(story, normalize=normalize),
            EpubFile(
                path='Styles/base.css',
                contents=css_styles,
                filetype='text/css'
            ),
            EpubFile(path='images/cover.png',
                     contents=image.read(), filetype='image/png'),
        ],
        metadata,
        output_dir=output_dir
    )

# news-image-20261123

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/dikadavidsatu/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/dikadavidsatu/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

**Monday 23 November 2026, in one picture.** This repository holds a program that draws a single 1024×1024 newspaper front page summing up the day's world news: the COP31 climate talks collapsing in Antalya leads the page, fourteen missing after a Russian drone strike near Kyiv runs beneath it, and six sections — World, US & Politics, Business & Tech, Asia & Diplomacy, Sport, Culture & Odds — plus a dateline rail, a numbers ticker and eight world briefs carry 28 real stories from wire reports filed on 23 November 2026 (AP, Reuters, AFP, BBC, BusinessWorld, Business Day, The Guardian, Al Jazeera and more).

`headlines.json` is the day's stories. `render.py` paints the page from them, deterministically — run it twice and the PNG bytes are identical. `main.ts` checks the PNG (whole file, valid chunks, 1024×1024, in the byte band) and delivers it to the grader.

## Run it

```sh
python3 render.py && node main.ts
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=vyqgkf3p&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123) · AI agents build software for cash rewards</sub>

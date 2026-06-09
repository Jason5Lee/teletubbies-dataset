# Teletubbies Episodes Dataset

This repository contains `teletubbies-episodes.csv`, a CSV catalog of 365 original
Teletubbies episodes. Each row represents one episode, ordered by its overall
episode number.

The dataset covers episodes `S01E01` through `S15E15`, from `31 March 1997` to
`21 December 2001`.

## CSV Columns

| Column | Description |
| --- | --- |
| `overall` | One-based episode number across the full series. |
| `season` | Season and episode code in `SxxEyy` format, such as `S01E01`. |
| `wikiUrl` | Episode page path on Teletubbies Wiki. This is stored as a relative path, not a complete URL. |
| `title` | Episode title. |
| `airdates` | Original air date text as listed by the source data, such as `31 March 1997`. |
| `ytId` | YouTube video ID. This is stored as the ID only, not a complete URL. |
| `ytLike` | YouTube like count. Added by `src/youtube_enrich.py` in enriched CSV output. |
| `ytView` | YouTube view count. Added by `src/youtube_enrich.py` in enriched CSV output. |

## URL Fields

The URL fields are stored compactly.

For `wikiUrl`, prepend the Teletubbies Wiki domain:

```text
https://teletubbies.fandom.com + wikiUrl
```

Example:

```text
/wiki/Ned%27s_Bicycle
https://teletubbies.fandom.com/wiki/Ned%27s_Bicycle
```

For `ytId`, prepend the YouTube watch URL prefix:

```text
https://www.youtube.com/watch?v= + ytId
```

Example:

```text
Tnw4Ze2tBIo
https://www.youtube.com/watch?v=Tnw4Ze2tBIo
```

## Fun Fact

The most liked and viewed Teletubbies episode is [Café Chocolate](https://www.youtube.com/watch?v=HOMCC9rIqe8). By the last time I checked, it had 59520 likes and 25890418 views.

# Portfolio visual system

The profile reads as a working interface. The opening panel shows the name selected in a design tool, with an inspect panel listing team, focus, location, stack, and 13 weeks of GitHub activity. Product cards follow, each with a small moving illustration of what the product does. The analytics panels come next: totals, a daily chart, two 30-day periods, a weekday bubble chart, weekly lines changed, a repository treemap, and language shares.

Deep indigo (#17162e) anchors every panel. Citron (#d8f36b) marks the latest period and primary emphasis. Violet (#8f88ff) carries most data marks, and pink (#ff8fc7) carries comparisons, averages, and removed lines. Language series use a fixed order: citron, pink, violet, amber (#ffb86b), sky (#56c7ec), with lilac grey for Other. That order keeps neighbouring series distinguishable under common colour-vision deficiencies; a language keeps its colour in every chart.

Space Grotesk is the display and reading face, in weights 400 to 700. JetBrains Mono is reserved for axis ticks, dates, and tool chrome. Values and labels are set in ink or muted ink; colour belongs to the marks beside them.

Charts use visible scales with round axis maximums, dated labels, and a legend whenever there is more than one series. Bars start at zero. Periods with no activity draw no mark. Bubble area, not radius, encodes contributions. The two 30-day periods share one scale. Lines added and removed share one scale around a zero line. Treemap blocks are proportional to code bytes.

Motion has three jobs. Marks grow from their baseline once when a panel first appears. Totals roll into place. After that, a slow highlight passes across each chart and the 7-day average redraws, so a panel still shows life when someone scrolls to it later. Product illustrations loop. Reduced motion shows every panel in its finished state.

Each panel has a narrow-screen layout that stacks the same blocks, a title and description for assistive technology, and a tooltip on every data mark for people who open the panel directly. Keep the narrow layouts and the README tables in sync with the data.

# CodeMemory product demo — narration

## Intro and empty workspace
CodeMemory is for the moment when a solved problem starts to fade from memory. It keeps coding history in one place so you can find an earlier problem, revisit an attempt, and see what your practice is teaching you.

This is a fresh workspace. There are no problems or submissions yet. The first step is to connect a public LeetCode profile, so CodeMemory knows which public history to look up.

## Public profile connection
Here, I enter the LeetCode username in the application and choose Connect. This public connection imports recent problem and submission records. It is separate from signing in: the username identifies the public profile, while a full-history sync needs authenticated credentials saved through Settings.

The public import finished successfully in this run: twenty problem records and twenty submissions were discovered and imported, with no failed records. This is the recent public window, not a claim that every historical submission has been downloaded.

## Settings and authenticated history
Settings provides the optional full-history workflow. The credentials are entered into the secure form and are not shown again after saving. CodeMemory checks the session before it stores anything. In this run, LeetCode did not return a usable submission list, so the credentials were not stored and a full-history sync could not proceed. I’m showing that result as it happened; the records you see next came from the successful public import.

## Search and revisit
In Submission History, the imported attempts are listed with their problem, status, language, and time. Search narrows the list as you type. For example, searching for three-sum brings back the matching problem and a related three-sum variant. Opening the problem connects that result to its topic tags and recorded attempt history. Here the 3Sum entry is an accepted Java submission with one recorded attempt. Source code and runtime were not present in this public import, so CodeMemory cannot make a code-level complexity assessment from this record.

## Learning insight
Analytics summarizes the same imported history. These numbers are computed from the records: twenty problems, twenty submissions, and an overall one-hundred-percent acceptance rate in this sample. The learning profile groups problems by topic. Arrays appear nine times, all solved; strings appear seven times, all solved. Expanding the array insight shows its evidence and a suggested next step: apply the topic in a harder or combined-topic problem. This is a useful way to turn a list of past solves into a concrete direction for future practice, while keeping the recommendation tied to the available data.

## Close
That is the workflow: connect a public profile, import its recent history, search and revisit individual attempts, then use the patterns in that history to guide what to practice next. Authenticated full-history sync remains unverified in this run.

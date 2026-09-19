import type { TopicStat } from "@/lib/types";
import { TableWrapper, TableHead, Th, Tbody, Tr, Td } from "@/components/app/data-table";
import { formatPercent } from "@/lib/format";

/**
 * Topic performance — the query-result view of the analytics page.
 *
 * Topics are already sorted by submission volume upstream; the default slice is
 * the top 10, which is the set a developer actually acts on.
 */
export function TopicTable({ topics, limit = 10 }: { topics: TopicStat[]; limit?: number }) {
  const rows = topics.slice(0, limit);

  return (
    <>
      <TableWrapper>
        <TableHead>
          <Th>Topic</Th>
          <Th align="right">Problems</Th>
          <Th align="right">Solved</Th>
          <Th align="right">Submissions</Th>
          <Th align="right">Acceptance</Th>
          <Th align="right">Success</Th>
        </TableHead>
        <Tbody>
          {rows.map((topic) => (
            <Tr key={topic.topic}>
              <Td className="font-medium text-text-primary">{topic.topic}</Td>
              <Td align="right" mono>
                {topic.totalProblems}
              </Td>
              <Td align="right" mono>
                {topic.solvedProblems}
              </Td>
              <Td align="right" mono>
                {topic.totalSubmissions}
              </Td>
              <Td align="right" mono>
                {formatPercent(topic.acceptanceRatePct)}
              </Td>
              <Td align="right" mono>
                {formatPercent(topic.successRatePct)}
              </Td>
            </Tr>
          ))}
        </Tbody>
      </TableWrapper>
      {topics.length > rows.length ? (
        <div className="border-t border-border-soft px-4 py-2.5 font-technical-sm text-text-faint">
          Top {rows.length} of {topics.length} topics, by submissions
        </div>
      ) : null}
    </>
  );
}

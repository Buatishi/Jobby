import type { GuideBlock } from "@/lib/guides/types";

export function GuideBlocks({ blocks }: { blocks: GuideBlock[] }) {
  return (
    <>
      {blocks.map((block, index) => {
        if (block.type === "paragraph") {
          return (
            <p className="mt-4 leading-7 text-neutral-700" key={index}>
              {block.text}
            </p>
          );
        }
        const List = block.type === "steps" ? "ol" : "ul";
        const marker = block.type === "steps" ? "list-decimal" : "list-disc";
        return (
          <List
            className={`mt-4 ${marker} space-y-2.5 pl-6 leading-7 text-neutral-700 marker:text-brand-green`}
            key={index}
          >
            {block.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </List>
        );
      })}
    </>
  );
}

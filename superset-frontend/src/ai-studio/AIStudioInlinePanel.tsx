import { css } from "@apache-superset/core/theme";
import AIStudioContent from "./AIStudioContent";
import type { AIStudioSection } from "./index";

type Props = {
  section: AIStudioSection;
  onSectionChange: (section: AIStudioSection) => void;
  onClose: () => void;
  onOpenPalette: () => void;
  onNotify: (message: string) => void;
  /** Fixed pixel width for a plain flex sibling (dashboard). Omit to fill
   * 100% of the parent instead, for a Splitter.Panel that already owns the
   * sizing (SQL Lab). */
  width?: number;
};

export default function AIStudioInlinePanel({ width, ...contentProps }: Props) {
  return (
    <div
      css={css`
        position: sticky;
        top: 0;
        flex: ${width ? `0 0 ${width}px` : "1"};
        width: ${width ? `${width}px` : "100%"};
        /* A dashboard's row (.dashboard-content) has no bounded height of its
         * own — with align-items:stretch (the default), a height:100% child
         * here would instead match its .grid-container sibling's *content*
         * height, which grows with however many chart rows the dashboard
         * has (and can be thousands of px on a long dashboard) rather than
         * the viewport. A dvh height sidesteps that entirely; sticky keeps
         * it pinned as the page scrolls. SQL Lab's own Splitter.Panel is
         * already properly viewport-bounded, so 100% is correct there. */
        height: ${width ? "100dvh" : "100%"};
        max-height: 100dvh;
        overflow: hidden;
        border-left: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(9, 18, 32, 0.97);
      `}
    >
      <AIStudioContent {...contentProps} />
    </div>
  );
}

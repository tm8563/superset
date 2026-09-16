import { css } from "@apache-superset/core/theme";

export default function Toast({ message }: { message: string }) {
  return (
    <output
      css={css`
        position: fixed;
        z-index: 1201;
        left: 50%;
        bottom: 25px;
        max-width: min(420px, calc(100vw - 32px));
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        background: #101b2d;
        color: #eef4ff;
        font-size: 11px;
        padding: 9px 13px;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.3);
        animation: ai-studio-toast 2.4s ease forwards;
        @keyframes ai-studio-toast {
          0% {
            opacity: 0;
            transform: translate(-50%, 12px);
          }
          10% {
            opacity: 1;
            transform: translate(-50%, 0);
          }
          85% {
            opacity: 1;
            transform: translate(-50%, 0);
          }
          100% {
            opacity: 0;
            transform: translate(-50%, 12px);
          }
        }
      `}
    >
      {message}
    </output>
  );
}

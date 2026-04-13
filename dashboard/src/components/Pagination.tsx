import { HiOutlineChevronLeft, HiOutlineChevronRight } from 'react-icons/hi2';

interface Props {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, totalPages, onPageChange }: Props) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-ws-border/40">
      <span className="text-xs font-mono text-ws-muted">
        Page {page} of {totalPages}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="p-1.5 rounded-lg text-ws-muted hover:text-ws-text hover:bg-white/[0.05] transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
        >
          <HiOutlineChevronLeft className="w-4 h-4" />
        </button>
        {Array.from({ length: totalPages }, (_, i) => i + 1)
          .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
          .reduce<(number | 'dots')[]>((acc, p, i, arr) => {
            if (i > 0 && p - (arr[i - 1] as number) > 1) acc.push('dots');
            acc.push(p);
            return acc;
          }, [])
          .map((item, i) =>
            item === 'dots' ? (
              <span key={`dots-${i}`} className="px-1 text-ws-muted text-xs">...</span>
            ) : (
              <button
                key={item}
                onClick={() => onPageChange(item)}
                className={`w-7 h-7 rounded-lg text-xs font-mono transition-colors cursor-pointer ${
                  page === item
                    ? 'bg-ws-green/15 text-ws-green'
                    : 'text-ws-muted hover:text-ws-text hover:bg-white/[0.05]'
                }`}
              >
                {item}
              </button>
            ),
          )}
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="p-1.5 rounded-lg text-ws-muted hover:text-ws-text hover:bg-white/[0.05] transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
        >
          <HiOutlineChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

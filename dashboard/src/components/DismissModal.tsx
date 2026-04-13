import type { QATicket } from '../api';
import { HiOutlineExclamationTriangle } from 'react-icons/hi2';

interface Props {
  ticket: QATicket;
  onCancel: () => void;
  onConfirm: () => void;
}

export default function DismissModal({ ticket, onCancel, onConfirm }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onCancel}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="glass-card rounded-2xl p-6 max-w-md w-full relative animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-full bg-red-500/10">
            <HiOutlineExclamationTriangle className="w-5 h-5 text-red-400" />
          </div>
          <h3 className="font-mono text-base font-semibold text-ws-text">Dismiss Ticket</h3>
        </div>
        <p className="text-sm text-ws-muted mb-3">
          Are you sure you want to dismiss this ticket from QA tracking? This action hides the
          ticket from the QA board.
        </p>
        <p className="text-sm text-ws-text bg-white/5 rounded-lg p-3 mb-6 font-medium">
          {ticket.subject}
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-ws-muted hover:text-ws-text rounded-lg glass-card transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm text-white bg-red-500/80 hover:bg-red-500 rounded-lg transition-colors font-medium cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}

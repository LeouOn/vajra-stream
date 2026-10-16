/**
 * AffirmationPanel — the Transmission card's Affirmation tab: forge an
 * empowering affirmation from the narrative's intention, copy or
 * regenerate it.
 *
 * @component
 */
import React from 'react';
import { Sparkles, RefreshCw, Copy, CheckCircle } from 'lucide-react';
import { Button, Typography } from 'antd';

const { Text } = Typography;

interface AffirmationPanelProps {
  affirmation: string | null;
  loading: boolean;
  copied: boolean;
  onGenerate: () => void;
  onCopy: () => void;
}

export default function AffirmationPanel({ affirmation, loading, copied, onGenerate, onCopy }: AffirmationPanelProps) {
  return (
    <div className="py-4">
      {!affirmation ? (
        <div className="text-center space-y-3 py-6">
          <Text type="secondary" style={{ fontSize: 13 }}>
            Forge a personal affirmation from this transmission's intention.
          </Text>
          <Button
            type="primary"
            onClick={onGenerate}
            loading={loading}
            icon={<Sparkles className="w-3.5 h-3.5" />}
            style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)', border: 'none' }}
          >
            Generate Affirmation
          </Button>
        </div>
      ) : (
        <div>
          <div className="flex justify-between items-center mb-3">
            <Text strong style={{ fontSize: 12, color: '#fbbf24' }}>Empowering Affirmation</Text>
            <Button
              size="small"
              icon={copied ? <CheckCircle className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              onClick={onCopy}
            >
              {copied ? 'Copied' : 'Copy'}
            </Button>
          </div>
          <blockquote className="border-l-4 border-amber-500/50 pl-4 pr-2 italic text-amber-100 text-base leading-relaxed whitespace-pre-wrap">
            "{affirmation}"
          </blockquote>
          <div className="mt-4 text-center">
            <Button
              size="small"
              type="default"
              onClick={onGenerate}
              loading={loading}
              icon={<RefreshCw className="w-3 h-3" />}
            >
              Regenerate
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

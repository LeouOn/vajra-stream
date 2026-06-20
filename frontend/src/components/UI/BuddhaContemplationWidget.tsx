/**
 * BuddhaContemplationWidget — deeplink card to the /buddhas route.
 *
 * Previously this rendered the full 88-Buddha contemplation inline and
 * polled the backend every 2s for loop status. That responsibility now
 * lives on the dedicated /buddhas route, which streams the same data
 * over the WebSocket (`BUDDHA_RECITATION_UPDATE` via `useWebSocketStable`).
 * This widget is reduced to a small card whose button navigates to the
 * full-page experience.
 *
 * @component
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from 'antd';
import { BookOpen, ArrowRight } from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';
import type { RecitationStatus } from '../../types';

interface Props {
  buddhaStatus?: RecitationStatus | null;
}

const BuddhaContemplationWidget: React.FC<Props> = (_props: Props) => {
  const navigate = useNavigate();

  const handleOpen = () => {
    audioFeedback.playClick();
    navigate('/buddhas');
  };

  return (
    <Card
      size="small"
      title={
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <BookOpen size={14} className="text-amber-400" />
          88 Buddhas
        </span>
      }
    >
      <Button
        type="primary"
        block
        icon={<ArrowRight size={14} />}
        onClick={handleOpen}
      >
        Open Contemplation
      </Button>
    </Card>
  );
};

export default BuddhaContemplationWidget;

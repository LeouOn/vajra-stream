/**
 * IllustrationCard — the "Sacred Illustration" generated from a narrative.
 * The image never carries numbers; the real values (moon at chart time, ...)
 * are captioned underneath by ImageCaptionFacts with their provenance.
 *
 * @component
 */
import React from 'react';
import { Image as ImageIcon } from 'lucide-react';
import { Card, Space, Tag, Typography } from 'antd';
import ImageCaptionFacts from '../ImageCaptionFacts';
import type { IllustrationResult } from './outlookNarrative';

const { Text, Paragraph } = Typography;

interface IllustrationCardProps {
  illustration: IllustrationResult;
}

export default function IllustrationCard({ illustration }: IllustrationCardProps) {
  return (
    <Card
      size="small"
      style={{ marginTop: 12 }}
      title={
        <Space size={6}>
          <ImageIcon size={13} className="text-pink-400" />
          <Text strong className="font-mono text-xs uppercase">Sacred Illustration</Text>
        </Space>
      }
      extra={
        <Space size={4}>
          {illustration.cached && (
            <Tag color="default" style={{ fontSize: 9 }}>CACHED</Tag>
          )}
          {illustration.provider_used && (
            <Tag color="purple" style={{ fontSize: 9 }}>{illustration.provider_used}</Tag>
          )}
          {illustration.model && (
            <Tag color="blue" style={{ fontSize: 9 }}>{illustration.model}</Tag>
          )}
          {typeof illustration.cost_usd === 'number' && (
            <Tag color="green" style={{ fontSize: 9 }}>${illustration.cost_usd.toFixed(4)}</Tag>
          )}
        </Space>
      }
    >
      <img
        src={illustration.image_data_url}
        alt={illustration.revised_prompt || 'Generated illustration'}
        style={{ width: '100%', borderRadius: 8 }}
      />
      <ImageCaptionFacts facts={illustration.caption_facts} />
      {illustration.revised_prompt && (
        <Paragraph
          type="secondary"
          style={{ marginTop: 8, marginBottom: 0, fontSize: 11, fontStyle: 'italic' }}
        >
          "{illustration.revised_prompt}"
        </Paragraph>
      )}
    </Card>
  );
}

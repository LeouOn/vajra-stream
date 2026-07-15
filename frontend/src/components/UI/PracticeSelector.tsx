/**
 * PracticeSelector — landing page for the canonical Buddhist practice library.
 *
 * Renders a meditative grid of practice cards (88 Buddhas, Green Tara,
 * White Tara, Zhunti, Medicine Buddha, Vajrasattva, Amitabha,
 * Avalokiteshvara, Heart Sutra). Each card uses a color accent driven by
 * the practice's traditional iconography — the accent bleeds into the
 * card border, top-bar, icon halo, and hover lift.
 *
 * Data flow: GET /api/v1/practices/list. While the backend is unreachable
 * (or offline), we fall back to a curated PRACTICES seed list so the page
 * is always populated and never empty — the user can browse even before
 * the backend responds. When the backend does respond, its data overrides
 * the seed by id.
 *
 * Search: simple client-side substring filter on name + description +
 * transliteration. No backend round-trip per keystroke.
 *
 * Navigation: clicking a card routes to `/practices/:id`, which renders
 * PracticeDetail. We use React Router (not AntD Menu) so cards remain
 * real anchor targets with the usual browser semantics.
 *
 * Design notes:
 *  - GPU-composited animation only (transform/opacity) on hover lift.
 *  - Color tokens come from lib/colors.js + Tailwind vajra-* utilities.
 *  - Each card is keyboard-focusable via the wrapping <Link>.
 *  - Loading + error states are first-class (skeleton grid + alert).
 *
 * @component
 * @route /practices
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Tag,
  Input,
  Empty,
  Skeleton,
  Alert,
  Space,
  Typography,
  Collapse,
} from 'antd';
import {
  Search,
  Compass,
} from 'lucide-react';
import { apiUrl } from '../../utils/api';
import { PRACTICES, type Practice } from './practicesCatalog';
import BijaResonanceChart from './BijaResonanceChart';

const { Title, Text, Paragraph } = Typography;

export type { Practice };

/**
 * PracticeCard — single practice in the grid. Wraps an AntD Card with a
 * color-accented top bar and an icon halo tinted to the practice color.
 *
 * The card itself is the click target; we use onClick + navigate() instead
 * of an anchor so we get the same SPA navigation semantics as the rest of
 * the app (no page reload, focus management kept consistent).
 */
interface PracticeCardProps {
  practice: Practice;
  onSelect: (id: string) => void;
}

const PracticeCard: React.FC<PracticeCardProps> = ({ practice, onSelect }) => {
  const Icon = practice.icon;
  const accentStyle = {
    // CSS variables let the gradient + halo reuse the practice color
    // without a runtime StyleSheet per-card.
    ['--practice-color' as string]: practice.color,
    ['--practice-color-rgb' as string]: practice.colorRgb,
  } as React.CSSProperties;

  return (
    <Card
      hoverable
      onClick={() => onSelect(practice.id)}
      onKeyDown={(e: React.KeyboardEvent<HTMLDivElement>) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(practice.id);
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`Open ${practice.name} practice`}
      style={accentStyle}
      styles={{
        body: { padding: 0 },
        header: { padding: 0, borderBottom: 'none' },
      }}
      className="group relative overflow-hidden bg-black/40 backdrop-blur-md border-white/10 transition-all duration-300 hover:-translate-y-1 hover:border-white/30 hover:shadow-[0_0_40px_rgba(var(--practice-color-rgb),0.35)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-purple-400"
      cover={
        // Top accent bar — the color is the practice's identity.
        <div
          className="h-1.5 w-full transition-all duration-300 group-hover:h-2"
          style={{
            background: `linear-gradient(90deg, var(--practice-color), transparent 80%)`,
            boxShadow: `0 0 18px rgba(var(--practice-color-rgb), 0.5)`,
          }}
        />
      }
    >
      <div className="px-5 pt-5 pb-6 flex flex-col gap-3">
        {/* Icon halo + title */}
        <div className="flex items-start gap-3">
          <div
            className="shrink-0 w-12 h-12 rounded-full flex items-center justify-center transition-transform duration-300 group-hover:scale-110"
            style={{
              background: `radial-gradient(circle, rgba(var(--practice-color-rgb),0.22), rgba(var(--practice-color-rgb),0.04))`,
              boxShadow: `inset 0 0 18px rgba(var(--practice-color-rgb),0.25), 0 0 14px rgba(var(--practice-color-rgb),0.18)`,
            }}
          >
            <Icon size={22} style={{ color: practice.color }} strokeWidth={1.7} />
          </div>
          <div className="flex-1 min-w-0">
            <Title
              level={5}
              className="!mb-0.5 !text-white transition-colors duration-300 group-hover:!text-[color:var(--practice-color)]"
            >
              {practice.name}
            </Title>
            {practice.transliteration && (
              <Text
                type="secondary"
                className="!text-xs !font-mono !tracking-wide"
              >
                {practice.transliteration}
              </Text>
            )}
          </div>
        </div>

        <Paragraph
          type="secondary"
          className="!mb-0 !text-sm !leading-relaxed !text-white/65 line-clamp-3"
        >
          {practice.description}
        </Paragraph>

        <div className="mt-1 flex items-center justify-between">
          <Tag
            color="default"
            className="!bg-white/5 !border-white/10 !text-white/70 !text-[10px] !font-mono !uppercase !tracking-widest !m-0"
          >
            {practice.benefits.length} benefit{practice.benefits.length === 1 ? '' : 's'}
          </Tag>
          <span
            className="text-xs font-medium opacity-60 group-hover:opacity-100 transition-opacity duration-300"
            style={{ color: practice.color }}
          >
            Begin →
          </span>
        </div>
      </div>
    </Card>
  );
};

export default function PracticeSelector(): React.ReactElement {
  const navigate = useNavigate();
  const [search, setSearch] = useState<string>('');
  const [practices, setPractices] = useState<Practice[]>(PRACTICES);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Pull the live practice list once on mount. The seed PRACTICES array
   * provides a populated fallback while the request is in flight or if
   * it fails (which is the common case in local dev — the endpoint
   * may not exist yet). Backend data is merged on top by id.
   */
  useEffect(() => {
    let cancelled = false;

    const fetchPractices = async (): Promise<void> => {
      try {
        const res = await fetch(apiUrl('/practices/list'));
        if (!res.ok) {
          throw new Error(`Backend returned ${res.status}`);
        }
        // Backend returns `{ practices: [...] }`. Some older clients (and
        // the offline fallback) may return a bare array — tolerate both.
        // Each backend row identifies itself with `practice_id`; the seed
        // catalog uses the field name `id`, so normalize here.
        const resp = await res.json();
        const rawList: Array<{
          practice_id?: string;
          id?: string;
          name: string;
          color?: string;
          benefits?: string[];
          primary_purpose?: string;
          mantra_count?: number;
        }> = Array.isArray(resp) ? resp : (resp.practices || []);

        if (cancelled) return;

        // Merge backend payload on top of the seed list. Seed wins on
        // missing fields so a partial backend payload still renders
        // beautifully (icon, transliteration, etc.).
        const seedById = new Map<string, Practice>(PRACTICES.map((p) => [p.id, p]));
        const merged: Practice[] = rawList.map((row) => {
          const rowId = row.practice_id ?? row.id ?? '';
          const seed = seedById.get(rowId);
          return {
            ...(seed ?? PRACTICES[0]),
            id: rowId,
            name: row.name,
            color: row.color || (seed?.color ?? '#8b5cf6'),
            benefits: row.benefits ?? seed?.benefits ?? [],
            // Backend to_public_dict does not emit a `mantra` field —
            // always fall back to the seed's curated mantra text.
            mantra: seed?.mantra,
          };
        });

        // If the backend returns nothing (empty list), keep the seed.
        setPractices(merged.length > 0 ? merged : PRACTICES);
        setError(null);
      } catch (err) {
        // Graceful fallback — the page is never empty.
        if (!cancelled) {
          setPractices(PRACTICES);
          setError(
            err instanceof Error
              ? `Couldn't reach the practice server (${err.message}). Showing the curated library.`
              : 'Showing the curated library.',
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void fetchPractices();
    return () => {
      cancelled = true;
    };
  }, []);

  /** Client-side filter on name / transliteration / description. */
  const filtered = useMemo<Practice[]>(() => {
    const q = search.trim().toLowerCase();
    if (!q) return practices;
    return practices.filter((p) => {
      return (
        p.name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        (p.transliteration ?? '').toLowerCase().includes(q) ||
        p.benefits.some((b) => b.toLowerCase().includes(q))
      );
    });
  }, [practices, search]);

  const handleSelect = (id: string): void => {
    navigate(`/practices/${id}`);
  };

  return (
    <div className="flex-1 h-full overflow-y-auto">
      <div className="max-w-7xl mx-auto px-6 py-10">
        {/* Header */}
        <Space orientation="vertical" size={20} className="w-full">
          <div className="text-center">
            <Space size={12} align="center" className="justify-center">
              <Compass size={28} className="text-purple-400" />
              <div>
                <Title level={2} className="!mb-1 !text-white">
                  Practice Library
                </Title>
                <Text type="secondary" className="!font-mono !text-sm">
                  Choose a practice to begin your recitation
                </Text>
              </div>
            </Space>
          </div>

          {/* Search */}
          <div className="max-w-xl mx-auto w-full">
            <Input
              size="large"
              allowClear
              placeholder="Search by name, transliteration, or benefit..."
              prefix={<Search size={16} className="text-white/40" />}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="!bg-black/40 !border-white/10 !text-white"
            />
          </div>

          {/* Soft error if backend was unreachable */}
          {error && !loading && (
            <Alert
              type="info"
              showIcon
              message="Practice server offline"
              description={error}
              className="!bg-amber-500/10 !border-amber-500/30"
            />
          )}

          {/* Grid */}
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {Array.from({ length: 6 }).map((_, i) => (
                <Card key={i} className="!bg-black/40 !border-white/10">
                  <Skeleton active paragraph={{ rows: 2 }} />
                </Card>
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <Empty
              description={
                <Text type="secondary">
                  No practices match “{search}”.
                </Text>
              }
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {filtered.map((practice) => (
                <PracticeCard
                  key={practice.id}
                  practice={practice}
                  onSelect={handleSelect}
                />
              ))}
            </div>
          )}

          {/* Bīja Resonance Chart */}
          <Collapse
            ghost
            size="small"
            className="!mt-8"
            items={[{
              key: 'bija',
              label: <Text className="!text-xs !font-mono !text-purple-300">⚖ Bīja Resonance Chart — Compare Deity Profiles</Text>,
              children: <BijaResonanceChart size={340} />,
            }]}
          />

          {/* Closing dedication */}
          <div className="text-center pt-8">
            <Text type="secondary" className="!text-xs !font-mono !italic">
              愿一切众生离苦得乐 · May all beings be free from suffering
            </Text>
          </div>
        </Space>
      </div>
    </div>
  );
}
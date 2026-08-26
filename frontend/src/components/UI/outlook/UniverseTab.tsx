/**
 * UniverseTab — realms / characters / populations management for the
 * Outlook workspace: grid views with filters, CRUD modals, and a
 * read-only populations overview. Selection state (which realm /
 * characters feed the Generator) stays in the dashboard shell.
 */
import React, { useMemo, useState } from 'react';
import {
  Button, Card, Col, Empty, Form, Input, InputNumber, Modal, Row,
  Select, Space, Switch, Tabs, Tag, Tooltip, Typography,
} from 'antd';
import { Edit2, Plus, Search, Trash2 } from 'lucide-react';
import { apiUrl } from '../../../utils/api';
import { audioFeedback } from '../../../utils/audioFeedback';
import { useUIStore } from '../../../stores/uiStore';
import type { Character, Population, Realm, UniverseTabId } from './outlookShared';

const { Text, Paragraph } = Typography;

interface UniverseTabProps {
  realms: Realm[];
  characters: Character[];
  populations: Population[];
  roles: string[];
  locationTypes: string[];
  selectedRealmId: string;
  onSelectRealm: (id: string) => void;
  selectedCharIds: Array<string | number>;
  onChangeSelectedCharIds: (next: Array<string | number>) => void;
  onRefreshUniverse: () => Promise<void> | void;
}

export default function UniverseTab({
  realms,
  characters,
  populations,
  roles,
  locationTypes,
  selectedRealmId,
  onSelectRealm,
  selectedCharIds,
  onChangeSelectedCharIds,
  onRefreshUniverse,
}: UniverseTabProps): React.ReactElement {
  const addToast = useUIStore(s => s.addToast);

  // ─── Universe Sub-tab ────────────────────────────────────
  const [universeTab, setUniverseTab] = useState<UniverseTab>('realms');

  // ─── CRUD Modals ─────────────────────────────────────────
  const [realmModalOpen, setRealmModalOpen] = useState<boolean>(false);
  const [editingRealm, setEditingRealm] = useState<Realm | null>(null);
  const [realmForm] = Form.useForm();

  const [charModalOpen, setCharModalOpen] = useState<boolean>(false);
  const [editingChar, setEditingChar] = useState<Character | null>(null);
  const [charForm] = Form.useForm();

  // ─── Filter State ────────────────────────────────────────
  const [realmSearch, setRealmSearch] = useState<string>('');
  const [realmTypeFilter, setRealmTypeFilter] = useState<string>('all');
  const [charSearch, setCharSearch] = useState<string>('');
  const [charRoleFilter, setCharRoleFilter] = useState<string>('all');

  // ─── Filtered Lists ──────────────────────────────────────

  const filteredRealms = useMemo<Realm[]>(() => {
    let result = realms;
    if (realmSearch) {
      const q = realmSearch.toLowerCase();
      result = result.filter(r =>
        r.name.toLowerCase().includes(q) ||
        (r.description || '').toLowerCase().includes(q) ||
        (r.realm_governor || '').toLowerCase().includes(q)
      );
    }
    if (realmTypeFilter !== 'all') result = result.filter(r => r.location_type === realmTypeFilter);
    return result;
  }, [realms, realmSearch, realmTypeFilter]);

  const filteredCharacters = useMemo<Character[]>(() => {
    let result = characters;
    if (charSearch) {
      const q = charSearch.toLowerCase();
      result = result.filter(c =>
        c.name.toLowerCase().includes(q) ||
        (c.description || '').toLowerCase().includes(q) ||
        (c.tags || []).some(t => t.toLowerCase().includes(q))
      );
    }
    if (charRoleFilter !== 'all') result = result.filter(c => c.role === charRoleFilter);
    return result;
  }, [characters, charSearch, charRoleFilter]);

  // ─── Generate Narrative ──────────────────────────────────

  // ─── Realm CRUD ──────────────────────────────────────────

  const openRealmModal = (realm: Realm | null = null): void => {
    setEditingRealm(realm);
    if (realm) {
      realmForm.setFieldsValue({
        ...realm,
        is_metaphysical: realm.is_metaphysical ?? true,
        latitude: realm.latitude ?? 0,
        longitude: realm.longitude ?? 0,
        dimension_frequency: realm.dimension_frequency ?? 528,
        priority: realm.priority ?? 5,
      });
    } else {
      realmForm.resetFields();
    }
    setRealmModalOpen(true);
  };

  const saveRealm = async (): Promise<void> => {
    try {
      const values = await realmForm.validateFields() as Record<string, unknown>;
      const payload: Record<string, unknown> = { ...values };
      if (payload.is_metaphysical) { payload.latitude = null; payload.longitude = null; }
      else { payload.latitude = parseFloat(String(payload.latitude)); payload.longitude = parseFloat(String(payload.longitude)); }

      const url = editingRealm
        ? apiUrl(`/outlook/locations/${editingRealm.id}`)
        : apiUrl('/outlook/locations');
      const method = editingRealm ? 'PUT' : 'POST';

      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (res.ok) {
        message.success(editingRealm ? 'Realm updated.' : 'Realm created.');
        setRealmModalOpen(false);
        void onRefreshUniverse();
      } else {
        const err = await res.json().catch(() => ({} as { detail?: string }));
        message.error(err.detail || `Failed to save realm: HTTP ${res.status}`);
        audioFeedback.playError();
      }
    } catch (e) {
      if ((e as { errorFields?: unknown }).errorFields) return;
      message.error('Failed to save realm.');
    }
  };

  const deleteRealm = async (id: string | number): Promise<void> => {
    Modal.confirm({
      title: 'Exile this realm?',
      content: 'This action cannot be undone.',
      okText: 'Delete', okType: 'danger', cancelText: 'Cancel',
      onOk: async () => {
        try {
          const res = await fetch(apiUrl(`/outlook/locations/${id}`), { method: 'DELETE' });
          if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
          message.success('Realm deleted.');
          void onRefreshUniverse();
        } catch (e) {
          addToast({ type: 'error', title: 'Could not delete realm', message: 'Backend unreachable or refused the request.', duration: 3000 });
        }
      },
    });
  };

  // ─── Character CRUD ──────────────────────────────────────

  const openCharModal = (char: Character | null = null): void => {
    setEditingChar(char);
    if (char) {
      charForm.setFieldsValue({ ...char, priority: char.priority ?? 5 });
    } else {
      charForm.resetFields();
    }
    setCharModalOpen(true);
  };

  const saveCharacter = async (): Promise<void> => {
    try {
      const values = await charForm.validateFields() as Record<string, unknown>;
      const url = editingChar
        ? apiUrl(`/outlook/characters/${editingChar.id}`)
        : apiUrl('/outlook/characters');
      const method = editingChar ? 'PUT' : 'POST';

      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) });
      if (res.ok) {
        message.success(editingChar ? 'Character updated.' : 'Character created.');
        setCharModalOpen(false);
        void onRefreshUniverse();
      } else {
        const err = await res.json().catch(() => ({} as { detail?: string }));
        message.error(err.detail || `Failed to save character: HTTP ${res.status}`);
        audioFeedback.playError();
      }
    } catch (e) {
      if ((e as { errorFields?: unknown }).errorFields) return;
      message.error('Failed to save character.');
    }
  };

  const deleteCharacter = async (id: string | number): Promise<void> => {
    Modal.confirm({
      title: 'Exile this character?',
      content: 'They will be removed from all future narratives.',
      okText: 'Exile', okType: 'danger', cancelText: 'Cancel',
      onOk: async () => {
        try {
          const res = await fetch(apiUrl(`/outlook/characters/${id}`), { method: 'DELETE' });
          if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
          message.success('Character exiled.');
          void onRefreshUniverse();
        } catch (e) {
          addToast({ type: 'error', title: 'Could not delete character', message: 'Backend unreachable or refused the request.', duration: 3000 });
        }
      },
    });
  };

  return (
    <>
{activeTab === 'universe' && (
  <Card size="small" styles={{ body: { padding: 0 } }}>
    <Tabs
      activeKey={universeTab}
      onChange={k => { setUniverseTab(k); audioFeedback.playClick(); }}
      style={{ padding: '0 16px' }}
      tabBarExtraContent={
        universeTab !== 'populations' && (
          <Button type="primary" size="small" icon={<Plus className="w-3 h-3" />}
            onClick={() => universeTab === 'realms' ? openRealmModal() : openCharModal()}>
            New {universeTab === 'realms' ? 'Realm' : 'Character'}
          </Button>
        )
      }
      items={[
        // ── Realms ──
        {
          key: 'realms',
          label: `Realms (${realms.length})`,
          children: (
            <div className="space-y-4">
              {/* Filters */}
              <Space wrap>
                <Input
                  size="small"
                  placeholder="Search realms..."
                  prefix={<Search className="w-3 h-3" />}
                  value={realmSearch}
                  onChange={e => setRealmSearch(e.target.value)}
                  style={{ width: 200 }}
                  allowClear
                />
                <Select
                  size="small"
                  value={realmTypeFilter}
                  onChange={setRealmTypeFilter}
                  style={{ width: 150 }}
                  options={[
                    { value: 'all', label: 'All Types' },
                    ...(locationTypes.map(t => ({ value: t, label: t.replace(/_/g, ' ') }))),
                  ]}
                />
                <Text type="secondary" style={{ fontSize: 11 }}>{filteredRealms.length} of {realms.length} realms</Text>
              </Space>

              {/* Realm Grid */}
              <Row gutter={[16, 16]}>
                {filteredRealms.map(r => (
                  <Col xs={24} md={12} key={r.id}>
                    <Card
                      size="small"
                      hoverable
                      className={r.id === selectedRealmId ? 'border-cyan-500' : ''}
                      actions={[
                        <Tooltip title="Set as setting" key="set"><Button type="text" size="small"
                          onClick={() => { setSelectedRealmId(r.id === selectedRealmId ? '' : r.id); audioFeedback.playClick(); }}>
                          {r.id === selectedRealmId ? '📍 Active' : '📍 Set'}</Button></Tooltip>,
                        <Tooltip title="Edit" key="edit"><Button type="text" size="small" icon={<Edit2 className="w-3 h-3" />}
                          onClick={() => openRealmModal(r)} /></Tooltip>,
                        <Tooltip title="Delete" key="del"><Button type="text" size="small" danger icon={<Trash2 className="w-3 h-3" />}
                          onClick={() => deleteRealm(r.id)} /></Tooltip>,
                      ]}
                    >
                      <Card.Meta
                        title={<span>{r.name} <Tag style={{ fontSize: 9 }}>{r.location_type?.replace(/_/g, ' ')}</Tag></span>}
                        description={
                          <div>
                            <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: 12, marginBottom: 8 }}>{r.description}</Paragraph>
                            <Space size={[4, 4]} wrap>
                              {r.is_metaphysical ? (
                                <>
                                  <Text type="secondary" style={{ fontSize: 10 }}>Freq: {r.dimension_frequency} Hz</Text>
                                  <Text type="secondary" style={{ fontSize: 10 }}>Coord: {r.celestial_coordinates || 'Uncharted'}</Text>
                                </>
                              ) : (
                                <>
                                  <Text type="secondary" style={{ fontSize: 10 }}>LAT/LON: {r.latitude}/{r.longitude}</Text>
                                </>
                              )}
                              <Text type="secondary" style={{ fontSize: 10 }}>Gov: {r.realm_governor || '—'}</Text>
                              <Text type="secondary" style={{ fontSize: 10 }}>Featured: {r.total_narratives_featured || 0}×</Text>
                            </Space>
                          </div>
                        }
                      />
                    </Card>
                  </Col>
                ))}
                {filteredRealms.length === 0 && (
                  <Col span={24}><Empty description="No realms match your filters" /></Col>
                )}
              </Row>
            </div>
          ),
        },
        // ── Characters ──
        {
          key: 'characters',
          label: `Characters (${characters.length})`,
          children: (
            <div className="space-y-4">
              <Space wrap>
                <Input size="small" placeholder="Search characters..." prefix={<Search className="w-3 h-3" />}
                  value={charSearch} onChange={e => setCharSearch(e.target.value)} style={{ width: 200 }} allowClear />
                <Select size="small" value={charRoleFilter} onChange={setCharRoleFilter} style={{ width: 130 }}
                  options={[{ value: 'all', label: 'All Roles' }, ...roles.map(r => ({ value: r, label: r.toUpperCase() }))]} />
                <Text type="secondary" style={{ fontSize: 11 }}>{filteredCharacters.length} of {characters.length}</Text>
              </Space>

              <Row gutter={[16, 16]}>
                {filteredCharacters.map(c => (
                  <Col xs={24} md={12} key={c.id}>
                    <Card
                      size="small"
                      hoverable
                      className={selectedCharIds.includes(c.id) ? 'border-purple-500' : ''}
                      actions={[
                        <Tooltip title={selectedCharIds.includes(c.id) ? 'Remove' : 'Add to narrative'} key="add">
                          <Button type="text" size="small"
                            onClick={() => setSelectedCharIds(prev => prev.includes(c.id) ? prev.filter(id => id !== c.id) : [...prev, c.id])}>
                            {selectedCharIds.includes(c.id) ? '✓ Added' : '👤 Add'}</Button></Tooltip>,
                        <Tooltip title="Edit" key="edit"><Button type="text" size="small" icon={<Edit2 className="w-3 h-3" />}
                          onClick={() => openCharModal(c)} /></Tooltip>,
                        <Tooltip title="Exile" key="del"><Button type="text" size="small" danger icon={<Trash2 className="w-3 h-3" />}
                          onClick={() => deleteCharacter(c.id)} /></Tooltip>,
                      ]}
                    >
                      <Card.Meta
                        title={<span>{c.name} <Tag style={{ fontSize: 9 }}>{c.role}</Tag></span>}
                        description={
                          <div>
                            <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: 12, marginBottom: 8 }}>{c.description}</Paragraph>
                            <Space size={[4, 4]} wrap>
                              {(c.tags || []).map(t => <Tag key={t} style={{ fontSize: 9 }}>{t}</Tag>)}
                            </Space>
                            <div style={{ marginTop: 8 }}>
                              <Text type="secondary" style={{ fontSize: 10 }}>Mantra: {c.mantra_preference || '—'} · Element: {c.elemental_anchor} · Featured: {c.total_narratives_featured || 0}×</Text>
                            </div>
                          </div>
                        }
                      />
                    </Card>
                  </Col>
                ))}
                {filteredCharacters.length === 0 && (
                  <Col span={24}><Empty description="No characters match your filters" /></Col>
                )}
              </Row>
            </div>
          ),
        },
        // ── Populations ──
        {
          key: 'populations',
          label: `Populations (${populations.length})`,
          children: (
            <Row gutter={[16, 16]}>
              {populations.map(p => (
                <Col xs={24} md={12} key={p.id}>
                  <Card size="small" hoverable>
                    <Card.Meta
                      title={<span>{p.name} {p.is_urgent && '🔥'}</span>}
                      description={
                        <div>
                          <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: 12 }}>{p.description}</Paragraph>
                          <Space size={[4, 4]} wrap style={{ marginTop: 8 }}>
                            <Tag color={p.is_active ? 'green' : 'default'}>{p.is_active ? 'ACTIVE' : 'INACTIVE'}</Tag>
                            <Text type="secondary" style={{ fontSize: 10 }}>Intentions: {p.intentions?.join(', ')}</Text>
                            <Text type="secondary" style={{ fontSize: 10 }}>Category: {p.category}</Text>
                            <Text type="secondary" style={{ fontSize: 10 }}>Priority: {p.priority}/10</Text>
                          </Space>
                        </div>
                      }
                    />
                  </Card>
                </Col>
              ))}
            </Row>
          ),
        },
      ]}
    />
  </Card>
)}

{/* ═══════════════════════════════════════════════════════
    HISTORY TAB
═══════════════════════════════════════════════════════ */}
{activeTab === 'history' && (

      {/* ═══════════════════════════════════════════════════════
          REALM MODAL
      ═══════════════════════════════════════════════════════ */}
      <Modal
        title={editingRealm ? 'Edit Realm' : 'Create New Realm'}
        open={realmModalOpen}
        onCancel={() => setRealmModalOpen(false)}
        onOk={saveRealm}
        okText="Save"
        width={640}
        destroyOnHidden
      >
        <Form form={realmForm} layout="vertical" size="small" initialValues={{ is_metaphysical: true, priority: 5, source_type: 'manual' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="Name" rules={[{ required: true }]}>
                <Input placeholder="e.g. Mount Kailash" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="location_type" label="Type">
                <Select options={(locationTypes || ['metaphysical_realm', 'earthly_sacred', 'cosmic_anchor', 'historical_academy']).map(t => ({ value: t, label: t.replace(/_/g, ' ') }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="is_metaphysical" label="Metaphysical Realm?" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.is_metaphysical !== cur.is_metaphysical}>
            {({ getFieldValue }) => {
              const isMeta = getFieldValue('is_metaphysical') !== false;
              return isMeta ? (
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="celestial_coordinates" label="Celestial Coordinates">
                      <Input placeholder="e.g. Northern Axis" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="dimension_frequency" label="Dimension Frequency (Hz)">
                      <InputNumber className="w-full" step={0.1} />
                    </Form.Item>
                  </Col>
                </Row>
              ) : (
                <Row gutter={16}>
                  <Col span={8}><Form.Item name="latitude" label="Latitude"><InputNumber className="w-full" step={0.0001} /></Form.Item></Col>
                  <Col span={8}><Form.Item name="longitude" label="Longitude"><InputNumber className="w-full" step={0.0001} /></Form.Item></Col>
                  <Col span={8}><Form.Item name="timezone" label="Timezone"><Input placeholder="UTC" /></Form.Item></Col>
                </Row>
              );
            }}
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="realm_governor" label="Governor"><Input placeholder="Ruler/Deity" /></Form.Item></Col>
            <Col span={8}><Form.Item name="astrological_anchor" label="Astro Anchor"><Input placeholder="e.g. Saturn MC" /></Form.Item></Col>
            <Col span={8}><Form.Item name="elemental_affinity" label="Element"><Input placeholder="e.g. Aether" /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="priority" label="Priority"><InputNumber className="w-full" min={1} max={10} /></Form.Item></Col>
            <Col span={12}><Form.Item name="source_type" label="Source"><Select options={['manual', 'generated', 'mythology', 'geographic'].map(s => ({ value: s, label: s }))} /></Form.Item></Col>
          </Row>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* ═══════════════════════════════════════════════════════
          CHARACTER MODAL
      ═══════════════════════════════════════════════════════ */}
      <Modal
        title={editingChar ? 'Edit Character' : 'Create Character'}
        open={charModalOpen}
        onCancel={() => setCharModalOpen(false)}
        onOk={saveCharacter}
        okText="Save"
        width={560}
        destroyOnHidden
      >
        <Form form={charForm} layout="vertical" size="small" initialValues={{ role: 'master', source_type: 'manual', elemental_anchor: 'space', priority: 5 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="Name" rules={[{ required: true }]}>
                <Input placeholder="e.g. Zen Master Zhao" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="role" label="Role">
                <Select options={(roles || ['master', 'student', 'alchemist', 'hero', 'deity', 'guardian', 'custom']).map(r => ({ value: r, label: r.toUpperCase() }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="dialogue_style" label="Dialogue Style">
            <Input placeholder="e.g. riddle-like, Zen Koans" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="mantra_preference" label="Mantra">
                <Input placeholder="om_mani_padme_hum" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="elemental_anchor" label="Elemental Anchor">
                <Select options={['space', 'earth', 'water', 'fire', 'air', 'aether'].map(e => ({ value: e, label: e }))} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="priority" label="Priority"><InputNumber className="w-full" min={1} max={10} /></Form.Item></Col>
            <Col span={12}><Form.Item name="source_type" label="Source"><Select options={['manual', 'generated', 'mythology', 'historical'].map(s => ({ value: s, label: s }))} /></Form.Item></Col>
          </Row>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

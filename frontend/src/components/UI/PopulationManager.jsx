/**
 * Population Manager Component
 *
 * CRUD interface for managing target populations that receive automated blessings.
 * Supports offline-first local storage with JSON persistence.
 */

import React, { useState, useEffect } from 'react';
import { Users, Plus, Edit2, Trash2, Folder, Globe, AlertCircle, Check, X } from 'lucide-react';

const API_BASE = 'http://localhost:8003/api/v1';

const PopulationManager = ({ className = '' }) => {
  const [populations, setPopulations] = useState([]);
  const [categories, setCategories] = useState([]);
  const [sourceTypes, setSourceTypes] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [filter, setFilter] = useState('all'); // all, active, urgent

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: 'missing_persons',
    source_type: 'local_directory',
    directory_path: '',
    mantra_preference: 'chenrezig',
    intentions: ['love', 'healing', 'peace'],
    repetitions_per_photo: 108,
    display_duration_ms: 2000,
    priority: 5,
    is_urgent: false,
    tags: [],
    notes: ''
  });

  // Load data on mount
  useEffect(() => {
    loadPopulations();
    loadCategories();
    loadSourceTypes();
  }, []);

  const loadPopulations = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/populations/`);
      if (response.ok) {
        const data = await response.json();
        setPopulations(data);
      }
    } catch (error) {
      console.error('Failed to load populations:', error);
    }
    setIsLoading(false);
  };

  const loadCategories = async () => {
    try {
      const response = await fetch(`${API_BASE}/populations/categories/list`);
      if (response.ok) {
        const data = await response.json();
        setCategories(data);
      }
    } catch (error) {
      console.error('Failed to load categories:', error);
    }
  };

  const loadSourceTypes = async () => {
    try {
      const response = await fetch(`${API_BASE}/populations/source-types/list`);
      if (response.ok) {
        const data = await response.json();
        setSourceTypes(data);
      }
    } catch (error) {
      console.error('Failed to load source types:', error);
    }
  };

  const createPopulation = async () => {
    try {
      const response = await fetch(`${API_BASE}/populations/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        await loadPopulations();
        resetForm();
        setShowCreateForm(false);
      }
    } catch (error) {
      console.error('Failed to create population:', error);
    }
  };

  const updatePopulation = async (id) => {
    try {
      const response = await fetch(`${API_BASE}/populations/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        await loadPopulations();
        setEditingId(null);
        resetForm();
      }
    } catch (error) {
      console.error('Failed to update population:', error);
    }
  };

  const deletePopulation = async (id) => {
    if (!confirm('Delete this population? This cannot be undone.')) return;

    try {
      const response = await fetch(`${API_BASE}/populations/${id}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await loadPopulations();
      }
    } catch (error) {
      console.error('Failed to delete population:', error);
    }
  };

  const toggleActive = async (id, currentActive) => {
    try {
      await fetch(`${API_BASE}/populations/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !currentActive })
      });
      await loadPopulations();
    } catch (error) {
      console.error('Failed to toggle active:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      category: 'missing_persons',
      source_type: 'local_directory',
      directory_path: '',
      mantra_preference: 'chenrezig',
      intentions: ['love', 'healing', 'peace'],
      repetitions_per_photo: 108,
      display_duration_ms: 2000,
      priority: 5,
      is_urgent: false,
      tags: [],
      notes: ''
    });
  };

  const startEdit = (pop) => {
    setFormData({
      name: pop.name,
      description: pop.description,
      category: pop.category,
      source_type: pop.source_type,
      directory_path: pop.directory_path || '',
      mantra_preference: pop.mantra_preference,
      intentions: pop.intentions,
      repetitions_per_photo: pop.repetitions_per_photo,
      display_duration_ms: pop.display_duration_ms,
      priority: pop.priority,
      is_urgent: pop.is_urgent,
      tags: pop.tags,
      notes: pop.notes
    });
    setEditingId(pop.id);
    setShowCreateForm(true);
  };

  // Filter populations
  const filteredPopulations = populations.filter(pop => {
    if (filter === 'active') return pop.is_active;
    if (filter === 'urgent') return pop.is_urgent;
    return true;
  });

  return (
    <div className={`bg-gray-800 rounded-lg ${className}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-900/50 to-purple-900/50 p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-bold text-white">Target Populations</h2>
          </div>
          <button
            onClick={() => {
              resetForm();
              setEditingId(null);
              setShowCreateForm(!showCreateForm);
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors flex items-center gap-2"
          >
            {showCreateForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            {showCreateForm ? 'Cancel' : 'Add Population'}
          </button>
        </div>
      </div>

      {/* Create/Edit Form */}
      {showCreateForm && (
        <div className="p-6 bg-gray-900 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">
            {editingId ? 'Edit Population' : 'Create New Population'}
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Name */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-1">Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="Missing Persons - California 2024"
                className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* Category */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Category *</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({...formData, category: e.target.value})}
                className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
              >
                {categories.map(cat => (
                  <option key={cat.value} value={cat.value}>{cat.name}</option>
                ))}
              </select>
            </div>

            {/* Source Type */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Source Type *</label>
              <select
                value={formData.source_type}
                onChange={(e) => setFormData({...formData, source_type: e.target.value})}
                className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
              >
                {sourceTypes.filter(s => s.available !== false).map(src => (
                  <option key={src.value} value={src.value}>{src.name}</option>
                ))}
              </select>
            </div>

            {/* Directory Path */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Photo Directory Path * <span className="text-gray-500 text-xs">(absolute path)</span>
              </label>
              <input
                type="text"
                value={formData.directory_path}
                onChange={(e) => setFormData({...formData, directory_path: e.target.value})}
                placeholder="/path/to/photos"
                className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none font-mono text-sm"
              />
            </div>

            {/* Mantra */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Mantra</label>
              <select
                value={formData.mantra_preference}
                onChange={(e) => setFormData({...formData, mantra_preference: e.target.value})}
                className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
              >
                <option value="chenrezig">Chenrezig (Compassion)</option>
                <option value="medicine_buddha">Medicine Buddha (Healing)</option>
                <option value="tara">Tara (Protection)</option>
                <option value="vajrasattva">Vajrasattva (Purification)</option>
                <option value="amitabha">Amitabha (Peaceful Passing)</option>
              </select>
            </div>

            {/* Priority */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Priority: {formData.priority}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={formData.priority}
                onChange={(e) => setFormData({...formData, priority: parseInt(e.target.value)})}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Low</span>
                <span>High</span>
              </div>
            </div>

            {/* Description */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                rows="2"
                className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none resize-none"
              />
            </div>

            {/* Urgent Checkbox */}
            <div className="md:col-span-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_urgent}
                  onChange={(e) => setFormData({...formData, is_urgent: e.target.checked})}
                  className="w-4 h-4"
                />
                <span className="text-sm text-gray-300">Mark as Urgent 🔥</span>
              </label>
            </div>
          </div>

          <div className="flex gap-2 mt-4">
            <button
              onClick={() => editingId ? updatePopulation(editingId) : createPopulation()}
              disabled={!formData.name || !formData.directory_path}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white px-6 py-2 rounded-lg font-semibold transition-colors"
            >
              {editingId ? 'Update' : 'Create'}
            </button>
            <button
              onClick={() => {
                setShowCreateForm(false);
                setEditingId(null);
                resetForm();
              }}
              className="bg-gray-700 hover:bg-gray-600 text-white px-6 py-2 rounded-lg font-semibold transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="p-4 bg-gray-900 border-b border-gray-700">
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            All ({populations.length})
          </button>
          <button
            onClick={() => setFilter('active')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === 'active' ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Active ({populations.filter(p => p.is_active).length})
          </button>
          <button
            onClick={() => setFilter('urgent')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === 'urgent' ? 'bg-red-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Urgent ({populations.filter(p => p.is_urgent).length})
          </button>
        </div>
      </div>

      {/* List */}
      <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
        {isLoading && (
          <div className="text-center py-8 text-gray-400">Loading...</div>
        )}

        {!isLoading && filteredPopulations.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            No populations found. Add one to get started!
          </div>
        )}

        {filteredPopulations.map(pop => (
          <div
            key={pop.id}
            className={`bg-gray-900 rounded-lg p-4 border ${
              pop.is_active ? 'border-gray-700' : 'border-gray-800 opacity-60'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-white font-semibold">{pop.name}</h3>
                  {pop.is_urgent && <span className="text-red-400 text-xl">🔥</span>}
                  {!pop.is_active && <span className="text-xs text-gray-500">(Inactive)</span>}
                </div>

                <div className="flex items-center gap-4 text-sm text-gray-400 mb-2">
                  <span className="flex items-center gap-1">
                    {pop.offline_available ? <Folder className="w-3 h-3" /> : <Globe className="w-3 h-3" />}
                    {pop.offline_available ? 'Local' : 'Online'}
                  </span>
                  <span>{pop.photo_count} photos</span>
                  <span>Priority: {pop.priority}</span>
                  <span>{pop.mantra_preference}</span>
                </div>

                {pop.total_blessings_sent > 0 && (
                  <div className="text-xs text-purple-400">
                    {pop.total_blessings_sent} blessings sent, {pop.total_mantras_repeated.toLocaleString()} mantras
                  </div>
                )}
              </div>

              <div className="flex gap-2 ml-4">
                <button
                  onClick={() => toggleActive(pop.id, pop.is_active)}
                  className={`p-2 rounded-lg transition-colors ${
                    pop.is_active
                      ? 'bg-green-600 hover:bg-green-700 text-white'
                      : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                  }`}
                  title={pop.is_active ? 'Deactivate' : 'Activate'}
                >
                  {pop.is_active ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => startEdit(pop)}
                  className="bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-lg transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => deletePopulation(pop.id)}
                  className="bg-red-600 hover:bg-red-700 text-white p-2 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Info */}
      <div className="p-4 bg-purple-900/20 border-t border-purple-500/30">
        <div className="flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-gray-300">
            <p className="mb-1">
              <strong className="text-purple-400">Populations</strong> are groups that receive automated blessings.
            </p>
            <p>
              Active populations are included in automation rotation. Manage priorities and urgency for intelligent scheduling.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PopulationManager;

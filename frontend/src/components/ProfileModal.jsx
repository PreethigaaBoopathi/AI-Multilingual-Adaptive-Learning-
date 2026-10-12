import React, { useState, useEffect } from 'react';
import { 
  X, User, Mail, Building, GraduationCap, Briefcase, 
  Languages, Image, LogOut, Check, AlertCircle, Loader2, Calendar
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const ProfileModal = ({ isOpen, onClose }) => {
  const { user, updateProfile, logout } = useAuth();

  const [name, setName] = useState('');
  const [organisation, setOrganisation] = useState('');
  const [orgType, setOrgType] = useState('College');
  const [department, setDepartment] = useState('');
  const [roleYear, setRoleYear] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState('en');
  const [profilePicture, setProfilePicture] = useState('');

  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (user) {
      setName(user.name || '');
      setOrganisation(user.organisation || '');
      setOrgType(user.org_type || 'College');
      setDepartment(user.department || '');
      setRoleYear(user.role_year || '');
      setPreferredLanguage(user.preferred_language || 'en');
      setProfilePicture(user.profile_picture || '');
      setSuccessMessage('');
      setErrorMessage('');
    }
  }, [user, isOpen]);

  if (!isOpen || !user) return null;

  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        setErrorMessage('Profile image must be less than 2MB.');
        return;
      }
      const reader = new FileReader();
      reader.onloadend = () => {
        setProfilePicture(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (!name.trim() || name.trim().length < 2) {
      setErrorMessage('Full name must be at least 2 characters long.');
      return;
    }

    try {
      setSaving(true);
      await updateProfile({
        name: name.trim(),
        organisation: organisation.trim(),
        org_type: orgType,
        department: department.trim(),
        role_year: roleYear.trim(),
        preferred_language: preferredLanguage,
        profile_picture: profilePicture,
      });
      setSuccessMessage('Profile updated successfully!');
      setTimeout(() => {
        setSuccessMessage('');
      }, 3000);
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || 'Failed to update profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div 
        className="relative w-full max-w-xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/70">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/10 dark:bg-indigo-400/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <User className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Academic Profile & Preferences</h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">View and update your personal learning details</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Messages */}
          {errorMessage && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 rounded-xl flex items-start space-x-2 text-rose-700 dark:text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}
          {successMessage && (
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/60 rounded-xl flex items-center space-x-2 text-emerald-700 dark:text-emerald-300 text-xs">
              <Check className="w-4 h-4 flex-shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Avatar Banner */}
          <div className="flex items-center space-x-4 p-4 rounded-xl bg-gradient-to-r from-indigo-50/70 via-slate-50 to-emerald-50/50 dark:from-slate-800/60 dark:via-slate-800/40 dark:to-slate-800/60 border border-slate-200/80 dark:border-slate-800">
            <div className="relative group">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-emerald-500 flex items-center justify-center text-white text-xl font-bold shadow-md overflow-hidden ring-2 ring-indigo-500/20">
                {profilePicture ? (
                  <img src={profilePicture} alt={name} className="w-full h-full object-cover" />
                ) : (
                  <span>{name ? name[0].toUpperCase() : 'U'}</span>
                )}
              </div>
              <label 
                htmlFor="profile-pic-modal"
                className="absolute -bottom-1 -right-1 bg-white dark:bg-slate-700 p-1 rounded-full shadow-md border border-slate-200 dark:border-slate-600 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
                title="Upload profile picture"
              >
                <Image className="w-3.5 h-3.5 text-slate-600 dark:text-slate-300" />
                <input 
                  type="file" 
                  id="profile-pic-modal" 
                  accept="image/*" 
                  className="hidden" 
                  onChange={handleImageUpload} 
                />
              </label>
            </div>

            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-extrabold text-slate-900 dark:text-white truncate">{name || 'Student Account'}</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate flex items-center mt-0.5">
                <Mail className="w-3.5 h-3.5 mr-1 text-slate-400" />
                {user.email}
              </p>
              {user.created_at && (
                <p className="text-[10px] text-slate-400 dark:text-slate-500 flex items-center mt-1">
                  <Calendar className="w-3 h-3 mr-1" />
                  Joined {new Date(user.created_at).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>

          {/* Form Fields */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
            {/* Full Name */}
            <div className="sm:col-span-2">
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Full Name</label>
              <div className="relative">
                <User className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alex Rivera"
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Email (Read-only) */}
            <div className="sm:col-span-2">
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Email Address <span className="text-[10px] text-slate-400 font-normal">(Primary account ID)</span>
              </label>
              <div className="relative">
                <Mail className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="email"
                  disabled
                  value={user.email}
                  className="w-full pl-9 pr-3 py-2 bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 rounded-xl cursor-not-allowed"
                />
              </div>
            </div>

            {/* Organisation / Institution Name */}
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Organisation / Institution</label>
              <div className="relative">
                <Building className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={organisation}
                  onChange={(e) => setOrganisation(e.target.value)}
                  placeholder="e.g. College of Engineering"
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Organisation Type */}
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Organisation Type</label>
              <select
                value={orgType}
                onChange={(e) => setOrgType(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="College">College</option>
                <option value="University">University</option>
                <option value="School">School</option>
                <option value="Company">Company</option>
                <option value="Other">Other</option>
              </select>
            </div>

            {/* Department / Course */}
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Department / Course</label>
              <div className="relative">
                <GraduationCap className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  placeholder="e.g. Computer Science & Eng"
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Year of study or professional role */}
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Year of Study or Role</label>
              <div className="relative">
                <Briefcase className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={roleYear}
                  onChange={(e) => setRoleYear(e.target.value)}
                  placeholder="e.g. 3rd Year / Researcher"
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Preferred Language */}
            <div className="sm:col-span-2">
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Preferred AI Study Language
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setPreferredLanguage('en')}
                  className={`flex items-center justify-center space-x-2 py-2 px-3 rounded-xl border text-xs font-semibold transition-all ${
                    preferredLanguage === 'en'
                      ? 'bg-indigo-50 dark:bg-indigo-950/60 border-indigo-500 text-indigo-700 dark:text-indigo-300 shadow-2xs'
                      : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                  }`}
                >
                  <Languages className="w-3.5 h-3.5" />
                  <span>English (EN)</span>
                </button>
                <button
                  type="button"
                  onClick={() => setPreferredLanguage('ta')}
                  className={`flex items-center justify-center space-x-2 py-2 px-3 rounded-xl border text-xs font-semibold transition-all ${
                    preferredLanguage === 'ta'
                      ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-500 text-emerald-700 dark:text-emerald-300 shadow-2xs'
                      : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                  }`}
                >
                  <Languages className="w-3.5 h-3.5" />
                  <span>தமிழ் (Tamil)</span>
                </button>
              </div>
            </div>
          </div>

          {/* Footer Controls */}
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center space-x-1.5 px-3 py-2 text-xs font-bold text-rose-600 hover:text-rose-700 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-xl transition-all"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Log Out</span>
            </button>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-all"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-xs transition-all disabled:opacity-60"
              >
                {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Save Changes</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

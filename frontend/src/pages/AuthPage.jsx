import React, { useState, useEffect } from 'react';
import { 
  BookOpen, Lock, Mail, User, Eye, EyeOff, Building, 
  GraduationCap, Briefcase, Languages, Image, ArrowRight, 
  Sparkles, AlertCircle, CheckCircle2, KeyRound, Loader2, RefreshCw
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ThemeToggle } from '../components/ThemeToggle';

export const AuthPage = ({ onAuthSuccess }) => {
  const { login, register, forgotPassword, resetPassword } = useAuth();

  const [mode, setMode] = useState('login'); // 'login', 'register', 'forgot'
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Password visibility toggles
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Login Form States (Always start blank)
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);

  // Ensure login fields are completely blank and clear any aggressive browser autofill
  useEffect(() => {
    setLoginEmail('');
    setLoginPassword('');
    const timer = setTimeout(() => {
      setLoginEmail('');
      setLoginPassword('');
    }, 100);
    return () => clearTimeout(timer);
  }, [mode]);

  // Register Form States
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [regOrganisation, setRegOrganisation] = useState('');
  const [regOrgType, setRegOrgType] = useState('College');
  const [regDepartment, setRegDepartment] = useState('');
  const [regRoleYear, setRegRoleYear] = useState('');
  const [regPreferredLanguage, setRegPreferredLanguage] = useState('en');
  const [regProfilePic, setRegProfilePic] = useState('');

  // Forgot Password States
  const [forgotEmail, setForgotEmail] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [forgotStep, setForgotStep] = useState(1); // 1: request code, 2: enter code & new pass

  // Handle Profile Picture File Selection
  const handleProfilePicUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        setErrorMessage('Profile picture must be under 2MB.');
        return;
      }
      const reader = new FileReader();
      reader.onloadend = () => {
        setRegProfilePic(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  // Submit Login
  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (!loginEmail.trim() || !loginPassword) {
      setErrorMessage('Please enter both your email and password.');
      return;
    }

    try {
      setLoading(true);
      await login(loginEmail.trim(), loginPassword, rememberMe);
      if (onAuthSuccess) onAuthSuccess();
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || 'Invalid email or password. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  // Submit Registration
  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (regName.trim().length < 2) {
      setErrorMessage('Full name must be at least 2 characters long.');
      return;
    }

    if (!regEmail.includes('@') || !regEmail.includes('.')) {
      setErrorMessage('Please enter a valid academic or professional email address.');
      return;
    }

    if (regPassword.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return;
    }

    if (regPassword !== regConfirmPassword) {
      setErrorMessage('Passwords do not match. Please verify your confirm password.');
      return;
    }

    try {
      setLoading(true);
      await register({
        name: regName.trim(),
        email: regEmail.trim(),
        password: regPassword,
        confirm_password: regConfirmPassword,
        organisation: regOrganisation.trim(),
        org_type: regOrgType,
        department: regDepartment.trim(),
        role_year: regRoleYear.trim(),
        preferred_language: regPreferredLanguage,
        profile_picture: regProfilePic,
      });
      setSuccessMessage('Account created successfully! Welcome to TextIQ.');
      setTimeout(() => {
        if (onAuthSuccess) onAuthSuccess();
      }, 500);
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || 'Registration failed. Please check your inputs or try a different email.');
    } finally {
      setLoading(false);
    }
  };

  // Submit Forgot Password Step 1: Request Code
  const handleRequestResetCode = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (!forgotEmail.trim() || !forgotEmail.includes('@')) {
      setErrorMessage('Please enter a valid registered email address.');
      return;
    }

    try {
      setLoading(true);
      const res = await forgotPassword(forgotEmail.trim());
      setSuccessMessage(res.message || 'Verification reset code generated.');
      if (res.reset_token) {
        setResetToken(res.reset_token); // Pre-fill for user convenience
      }
      setForgotStep(2);
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || 'No account found with this email address.');
    } finally {
      setLoading(false);
    }
  };

  // Submit Forgot Password Step 2: Set New Password
  const handleResetPasswordSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (!resetToken.trim()) {
      setErrorMessage('Please enter the 6-digit verification code.');
      return;
    }

    if (newPassword.length < 6) {
      setErrorMessage('New password must be at least 6 characters long.');
      return;
    }

    try {
      setLoading(true);
      const res = await resetPassword(forgotEmail.trim(), resetToken.trim(), newPassword);
      setSuccessMessage(res.message || 'Password successfully reset! You can now log in.');
      setLoginEmail(forgotEmail.trim());
      setLoginPassword('');
      setTimeout(() => {
        setMode('login');
        setForgotStep(1);
      }, 1500);
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || 'Invalid or expired verification code.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 py-12 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">
      {/* Discreet Theme Switcher */}
      <div className="absolute top-4 right-4 sm:top-6 sm:right-6 z-10">
        <ThemeToggle />
      </div>

      <div className={`w-full ${mode === 'register' ? 'max-w-xl' : 'max-w-md'} bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl rounded-2xl p-6 sm:p-8 space-y-6 transition-all duration-200 relative z-10`}>
        
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-700 to-emerald-500 flex items-center justify-center text-white mx-auto shadow-md shadow-indigo-500/20">
            <BookOpen className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            {mode === 'login' && 'Student & Educator Sign In'}
            {mode === 'register' && 'Create Your TextIQ Account'}
            {mode === 'forgot' && 'Reset Account Password'}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
            {mode === 'login' && 'Access course intelligence, bilingual study aids & adaptive learning models'}
            {mode === 'register' && 'Join the multilingual AI learning studio with personalised curriculum tracking'}
            {mode === 'forgot' && 'Verify your academic email and establish a secure new password'}
          </p>
        </div>

        {/* Top Tab Switcher (Visible on login & register) */}
        {mode !== 'forgot' && (
          <div className="grid grid-cols-2 gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400">
            <button
              type="button"
              onClick={() => { setMode('login'); setErrorMessage(''); setSuccessMessage(''); }}
              className={`py-2 rounded-lg transition-all ${
                mode === 'login'
                  ? 'bg-white dark:bg-slate-700 text-indigo-700 dark:text-indigo-300 shadow-2xs font-bold'
                  : 'hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); setErrorMessage(''); setSuccessMessage(''); }}
              className={`py-2 rounded-lg transition-all ${
                mode === 'register'
                  ? 'bg-white dark:bg-slate-700 text-indigo-700 dark:text-indigo-300 shadow-2xs font-bold'
                  : 'hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Sign Up
            </button>
          </div>
        )}

        {/* Global Alert Messages */}
        {errorMessage && (
          <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 rounded-xl flex items-start space-x-2 text-rose-700 dark:text-rose-300 text-xs animate-in fade-in">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}
        {successMessage && (
          <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/60 rounded-xl flex items-center space-x-2 text-emerald-700 dark:text-emerald-300 text-xs animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* ---------------- LOGIN FORM ---------------- */}
        {mode === 'login' && (
          <form onSubmit={handleLoginSubmit} className="space-y-4" autoComplete="off">
            {/* Hidden dummy fields to neutralize aggressive Chromium/Edge autofill */}
            <input
              type="text"
              name="fake_autofill_username"
              className="sr-only opacity-0 h-0 w-0 absolute -z-10 pointer-events-none"
              tabIndex="-1"
              aria-hidden="true"
              autoComplete="off"
            />
            <input
              type="password"
              name="fake_autofill_password"
              className="sr-only opacity-0 h-0 w-0 absolute -z-10 pointer-events-none"
              tabIndex="-1"
              aria-hidden="true"
              autoComplete="new-password"
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="email"
                  name="user_email_address"
                  id="user_email_address"
                  required
                  autoComplete="off"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck="false"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="Enter email"
                  className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => { setMode('forgot'); setForgotEmail(loginEmail); setErrorMessage(''); setSuccessMessage(''); }}
                  className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline font-semibold"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="user_account_secret"
                  id="user_account_secret"
                  required
                  autoComplete="new-password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="Enter password"
                  className="w-full pl-9 pr-10 py-2 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  tabIndex="-1"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <label className="flex items-center space-x-2 text-slate-600 dark:text-slate-400 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-3.5 h-3.5 rounded-sm text-indigo-600 focus:ring-indigo-500 border-slate-300 dark:border-slate-700"
                />
                <span>Remember this session</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all flex items-center justify-center space-x-1.5 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Learning Studio</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>

            <p className="text-center text-xs text-slate-500 dark:text-slate-400 pt-1">
              Don't have an account yet?{' '}
              <button
                type="button"
                onClick={() => { setMode('register'); setErrorMessage(''); setSuccessMessage(''); }}
                className="text-indigo-600 dark:text-indigo-400 font-bold hover:underline"
              >
                Sign Up here
              </button>
            </p>
          </form>
        )}

        {/* ---------------- REGISTER FORM ---------------- */}
        {mode === 'register' && (
          <form onSubmit={handleRegisterSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              
              {/* Full Name */}
              <div className="sm:col-span-2">
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    placeholder="Enter your full name"
                    className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Email Address */}
              <div className="sm:col-span-2">
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Institution or Personal Email <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="email"
                    required
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="Enter email"
                    className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Password <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="Enter password"
                    className="w-full pl-9 pr-8 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                    tabIndex="-1"
                  >
                    {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Confirm Password <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    value={regConfirmPassword}
                    onChange={(e) => setRegConfirmPassword(e.target.value)}
                    placeholder="Confirm password"
                    className="w-full pl-9 pr-8 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                    tabIndex="-1"
                  >
                    {showConfirmPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Organisation Name */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Organisation / Institution
                </label>
                <div className="relative">
                  <Building className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={regOrganisation}
                    onChange={(e) => setRegOrganisation(e.target.value)}
                    placeholder="e.g. Stanford / Anna University"
                    className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Organisation Type */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Organisation Type
                </label>
                <select
                  value={regOrgType}
                  onChange={(e) => setRegOrgType(e.target.value)}
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
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Department / Course
                </label>
                <div className="relative">
                  <GraduationCap className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={regDepartment}
                    onChange={(e) => setRegDepartment(e.target.value)}
                    placeholder="e.g. Computer Science"
                    className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Year of study or professional role */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Year of Study or Role
                </label>
                <div className="relative">
                  <Briefcase className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={regRoleYear}
                    onChange={(e) => setRegRoleYear(e.target.value)}
                    placeholder="e.g. 2nd Year / Faculty"
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
                    onClick={() => setRegPreferredLanguage('en')}
                    className={`flex items-center justify-center space-x-2 py-2 px-3 rounded-xl border font-semibold transition-all ${
                      regPreferredLanguage === 'en'
                        ? 'bg-indigo-50 dark:bg-indigo-950/60 border-indigo-500 text-indigo-700 dark:text-indigo-300 shadow-2xs'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                    }`}
                  >
                    <Languages className="w-3.5 h-3.5" />
                    <span>English (EN)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setRegPreferredLanguage('ta')}
                    className={`flex items-center justify-center space-x-2 py-2 px-3 rounded-xl border font-semibold transition-all ${
                      regPreferredLanguage === 'ta'
                        ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-500 text-emerald-700 dark:text-emerald-300 shadow-2xs'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                    }`}
                  >
                    <Languages className="w-3.5 h-3.5" />
                    <span>தமிழ் (Tamil)</span>
                  </button>
                </div>
              </div>

              {/* Optional Profile Picture Upload */}
              <div className="sm:col-span-2">
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Profile Picture <span className="text-[10px] text-slate-400 font-normal">(Optional)</span>
                </label>
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-400 overflow-hidden flex-shrink-0">
                    {regProfilePic ? (
                      <img src={regProfilePic} alt="Preview" className="w-full h-full object-cover" />
                    ) : (
                      <Image className="w-5 h-5" />
                    )}
                  </div>
                  <label className="flex-1 cursor-pointer">
                    <div className="px-3 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700/60 border border-slate-300 dark:border-slate-700 rounded-xl text-center transition-colors">
                      {regProfilePic ? 'Change Image (Under 2MB)' : 'Choose Image (JPG, PNG)'}
                    </div>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleProfilePicUpload}
                    />
                  </label>
                  {regProfilePic && (
                    <button
                      type="button"
                      onClick={() => setRegProfilePic('')}
                      className="text-xs text-rose-500 hover:underline"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all flex items-center justify-center space-x-1.5 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Creating Account...</span>
                </>
              ) : (
                <>
                  <span>Complete Registration</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>

            <p className="text-center text-xs text-slate-500 dark:text-slate-400">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => { setMode('login'); setErrorMessage(''); setSuccessMessage(''); }}
                className="text-indigo-600 dark:text-indigo-400 font-bold hover:underline"
              >
                Sign In
              </button>
            </p>
          </form>
        )}

        {/* ---------------- FORGOT PASSWORD FLOW ---------------- */}
        {mode === 'forgot' && (
          <div className="space-y-4">
            {forgotStep === 1 ? (
              <form onSubmit={handleRequestResetCode} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Your Registered Email
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="email"
                      required
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      placeholder="Enter email"
                      className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all flex items-center justify-center space-x-1.5 disabled:opacity-60"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Generating Code...</span>
                    </>
                  ) : (
                    <>
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>Send 6-Digit Reset Code</span>
                    </>
                  )}
                </button>
              </form>
            ) : (
              <form onSubmit={handleResetPasswordSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    6-Digit Verification Code
                  </label>
                  <div className="relative">
                    <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      required
                      maxLength="6"
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      placeholder="e.g. 581920"
                      className="w-full pl-9 pr-3 py-2 text-xs font-mono tracking-widest bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    New Password
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter new password"
                      className="w-full pl-9 pr-10 py-2 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                      tabIndex="-1"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all flex items-center justify-center space-x-1.5 disabled:opacity-60"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Updating Password...</span>
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Update Password & Log In</span>
                    </>
                  )}
                </button>
              </form>
            )}

            <div className="pt-2 text-center">
              <button
                type="button"
                onClick={() => { setMode('login'); setErrorMessage(''); setSuccessMessage(''); setForgotStep(1); }}
                className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline"
              >
                ← Back to Sign In
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

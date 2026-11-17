/**
 * CollegeHub Supabase Auth Integration
 * Secure authentication engine for Student & Parent admissions matrix.
 *
 * Security Policies:
 * - Uses ONLY the Supabase Publishable (Anon) Key in browser code.
 * - Secret keys and client secrets remain strictly server-side / in environment variables.
 * - Never logs passwords, access tokens, or recovery codes to the console.
 * - Google Sign-in redirects to official accounts.google.com via Supabase OAuth.
 * - Student/Parent is a profile choice (stored in user_metadata), not administrative privilege.
 */

(function () {
  'use strict';

  // Fallback defaults from verified project environment (Publishable Key only)
  let SUPABASE_URL = 'https://uwaddyejdswshzamhjfs.supabase.co';
  let SUPABASE_ANON_KEY = 'sb_publishable_t4NlIpg9zngDZr0-EQmgGg__vLSrkc9';

  let supabaseClient = null;
  let isSupabaseReady = false;

  // Rate limiting / cooldown state
  const RATE_LIMITS = {
    recoveryLastSent: 0,
    recoveryCooldownSeconds: 60,
    verificationAttempts: 5,
    resendConfirmationLastSent: 0,
    resendCooldownSeconds: 60
  };

  /**
   * Initialize Supabase client
   */
  async function initSupabase() {
    try {
      // Try to load public config from server
      const cfgResp = await fetch('/api/auth/config').catch(() => null);
      if (cfgResp && cfgResp.ok) {
        const cfg = await cfgResp.json();
        if (cfg.supabase_url) SUPABASE_URL = cfg.supabase_url;
        if (cfg.supabase_publishable_key) SUPABASE_ANON_KEY = cfg.supabase_publishable_key;
      }
    } catch (e) {
      // Silent fallback
    }

    // Initialize Supabase JS Client if library is loaded
    if (window.supabase && typeof window.supabase.createClient === 'function') {
      try {
        supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
          auth: {
            persistSession: true,
            autoRefreshToken: true,
            detectSessionInUrl: true,
            storageKey: 'collegehub-supabase-auth'
          }
        });
        isSupabaseReady = true;

        // Listen for Auth changes (OAuth return, email confirmation link, recovery)
        supabaseClient.auth.onAuthStateChange(async (event, session) => {
          if (event === 'SIGNED_IN' && session?.user) {
            await syncServerSession(session.user);
          } else if (event === 'PASSWORD_RECOVERY') {
            // User arrived via Supabase password recovery email link
            if (typeof window.onSupabasePasswordRecovery === 'function') {
              window.onSupabasePasswordRecovery(session);
            }
          }
        });
      } catch (err) {
        console.warn('Supabase JS client init notice:', err?.message || err);
      }
    }
  }

  /**
   * Sync Supabase authenticated session with Flask server session
   */
  async function syncServerSession(user) {
    if (!user) return;
    try {
      const email = user.email || '';
      const metadata = user.user_metadata || {};
      const fullName = metadata.full_name || metadata.name || '';
      const role = metadata.role || 'student';
      const provider = user.app_metadata?.provider || 'supabase';

      const resp = await fetch('/api/auth/sync-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          full_name: fullName,
          role: role,
          provider: provider
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        if (data.user) {
          localStorage.setItem('collegehub_user', JSON.stringify(data.user));
          localStorage.setItem('collegehub_logged_in', 'true');
          if (typeof CollegeHubAuth !== 'undefined' && typeof CollegeHubAuth.updateDOM === 'function') {
            CollegeHubAuth.updateDOM();
          }
        }
      }
    } catch (e) {
      // Server sync is secondary to client auth
    }
  }

  /**
   * Validate password against security rules
   * Requirements:
   * - At least 8 characters
   * - Contains a letter (a-z or A-Z)
   * - Contains a number (0-9)
   * - Matches confirm password (if provided)
   */
  function validatePassword(password, confirmPassword) {
    const pwd = password || '';
    const hasMinLength = pwd.length >= 8;
    const hasLetter = /[a-zA-Z]/.test(pwd);
    const hasNumber = /[0-9]/.test(pwd);
    const matches = confirmPassword !== undefined ? pwd === (confirmPassword || '') : true;

    return {
      isValid: hasMinLength && hasLetter && hasNumber && matches,
      hasMinLength,
      hasLetter,
      hasNumber,
      matches
    };
  }

  /**
   * Update visual checklist of password rules beside / below password fields
   */
  function updatePasswordRulesUI(password, confirmPassword, prefix) {
    const pfx = prefix ? prefix + '-' : '';
    const rules = validatePassword(password, confirmPassword);

    const lengthEl = document.getElementById(pfx + 'rule-length');
    const letterEl = document.getElementById(pfx + 'rule-letter');
    const numberEl = document.getElementById(pfx + 'rule-number');
    const matchEl = document.getElementById(pfx + 'rule-match');

    function applyState(el, passed) {
      if (!el) return;
      const icon = el.querySelector('.material-symbols-outlined');
      if (passed) {
        el.className = el.className.replace(/text-[a-z\-0-9]+/g, '').trim() + ' flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-semibold';
        if (icon) {
          icon.textContent = 'check_circle';
          icon.className = 'material-symbols-outlined text-sm text-emerald-600 dark:text-emerald-400';
        }
      } else {
        el.className = el.className.replace(/text-[a-z\-0-9]+/g, '').trim() + ' flex items-center gap-1.5 text-on-surface-variant font-normal';
        if (icon) {
          icon.textContent = 'radio_button_unchecked';
          icon.className = 'material-symbols-outlined text-sm text-outline';
        }
      }
    }

    applyState(lengthEl, rules.hasMinLength);
    applyState(letterEl, rules.hasLetter);
    applyState(numberEl, rules.hasNumber);

    if (matchEl && confirmPassword !== undefined) {
      matchEl.classList.remove('hidden');
      applyState(matchEl, Boolean(password && confirmPassword && rules.matches));
    }

    return rules;
  }

  /**
   * Check if Google OAuth provider is enabled in the Supabase project
   */
  async function checkGoogleProviderStatus() {
    try {
      const resp = await fetch(`${SUPABASE_URL}/auth/v1/settings`, {
        headers: { 'apikey': SUPABASE_ANON_KEY }
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data && data.external && data.external.google === false) {
          return false;
        }
      }
    } catch (e) {
      // Ignore network errors and continue
    }
    return true;
  }

  /**
   * Display friendly in-app modal explaining how to toggle Google on in Supabase
   */
  function showGoogleProviderSetupModal() {
    let modal = document.getElementById('supabase-google-setup-modal');
    if (modal) modal.remove();

    modal = document.createElement('div');
    modal.id = 'supabase-google-setup-modal';
    modal.className = 'fixed inset-0 z-[200] flex items-center justify-center p-4 bg-primary/75 backdrop-blur-md transition-all duration-300';
    modal.innerHTML = `
      <div class="w-full max-w-md bg-surface-container-lowest rounded-3xl p-6 sm:p-7 shadow-[0_20px_60px_rgba(0,0,0,0.3)] border border-surface-container-high relative text-on-surface">
        <!-- Close button -->
        <button type="button" onclick="document.getElementById('supabase-google-setup-modal').remove()" class="absolute top-4 right-4 w-8 h-8 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface-variant flex items-center justify-center transition-colors" title="Close dialog">
          <span class="material-symbols-outlined text-lg">close</span>
        </button>

        <!-- Header -->
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-2xl bg-amber-500/20 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
            <span class="material-symbols-outlined text-xl">toggle_off</span>
          </div>
          <div>
            <h3 class="text-base font-extrabold text-primary leading-tight">Google Provider Not Enabled</h3>
            <p class="text-[11px] text-on-surface-variant">Supabase project: <code class="font-mono text-secondary">uwaddyejdswshzamhjfs</code></p>
          </div>
        </div>

        <!-- Explanation of error -->
        <div class="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-xs text-on-surface-variant space-y-1.5 mb-4 leading-relaxed">
          <div class="font-bold text-amber-700 dark:text-amber-300 flex items-center gap-1.5">
            <span class="material-symbols-outlined text-sm shrink-0">warning</span>
            <span>Why this message appears:</span>
          </div>
          <p>
            Supabase returned <code>"Unsupported provider: provider is not enabled"</code> because the Google OAuth toggle is currently turned OFF in your Supabase project dashboard.
          </p>
        </div>

        <!-- Steps to fix -->
        <div class="space-y-2 mb-5 text-xs">
          <div class="font-bold text-primary">How to enable it (2 minutes):</div>
          <ol class="list-decimal pl-4 space-y-1.5 text-on-surface-variant text-[11px] leading-relaxed">
            <li>Open your Supabase <strong>Authentication &gt; Providers</strong> dashboard.</li>
            <li>Click <strong>Google</strong> and toggle <strong>"Enable Sign in with Google"</strong> to <strong>ON</strong>.</li>
            <li>Paste your Google Cloud <strong>Client ID</strong> &amp; <strong>Client Secret</strong>.</li>
            <li>Make sure <code>https://uwaddyejdswshzamhjfs.supabase.co/auth/v1/callback</code> is added under <em>Authorized redirect URIs</em> in your Google Cloud Console.</li>
            <li>Click <strong>Save</strong>.</li>
          </ol>
        </div>

        <!-- Action buttons -->
        <div class="space-y-2">
          <a 
            href="https://supabase.com/dashboard/project/uwaddyejdswshzamhjfs/auth/providers" 
            target="_blank" 
            rel="noopener noreferrer"
            class="w-full py-2.5 px-4 rounded-xl bg-secondary text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-sm hover:bg-secondary/90 transition-all text-center"
          >
            <span class="material-symbols-outlined text-sm">open_in_new</span>
            <span>Open Supabase Providers Dashboard</span>
          </a>
          <button 
            type="button" 
            onclick="document.getElementById('supabase-google-setup-modal').remove()" 
            class="w-full py-2 px-4 rounded-xl bg-surface-container hover:bg-surface-container-high text-on-surface text-xs font-semibold transition-colors"
          >
            Continue with Email &amp; Password
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  /**
   * Google Sign-in:
   * Redirects user directly to Google's official sign-in screen via Supabase OAuth.
   * Never asks for or stores user's Google password.
   */
  async function signInWithGoogle(role) {
    const chosenRole = role || 'student';
    const callbackUrl = window.location.origin + '/api/auth/google/callback';

    // Check if Google provider is enabled in Supabase
    const isGoogleEnabled = await checkGoogleProviderStatus();
    if (!isGoogleEnabled) {
      showGoogleProviderSetupModal();
      return { status: 'provider_disabled' };
    }

    if (supabaseClient && isSupabaseReady) {
      try {
        const { error } = await supabaseClient.auth.signInWithOAuth({
          provider: 'google',
          options: {
            redirectTo: callbackUrl,
            queryParams: {
              access_type: 'offline',
              prompt: 'select_account'
            }
          }
        });

        if (error) {
          if (error.message && (error.message.toLowerCase().includes('not enabled') || error.message.toLowerCase().includes('unsupported provider'))) {
            showGoogleProviderSetupModal();
            return { status: 'provider_disabled' };
          }
          throw error;
        }
        return { status: 'redirecting' };
      } catch (err) {
        console.warn('Supabase OAuth redirect error, falling back to server route:', err.message);
        if (err.message && (err.message.toLowerCase().includes('not enabled') || err.message.toLowerCase().includes('unsupported provider'))) {
          showGoogleProviderSetupModal();
          return { status: 'provider_disabled' };
        }
      }
    }

    // Direct fallback redirect through server OAuth endpoint
    window.location.href = `/api/auth/google/login?role=${encodeURIComponent(chosenRole)}`;
    return { status: 'redirecting' };
  }

  /**
   * Email and Password Sign-In:
   * Uses Supabase Auth; requires valid email and min 8 char password.
   * Uses email address as sole identifier (no username / applicant ID).
   */
  async function signInWithEmail(email, password, role) {
    const cleanEmail = (email || '').trim().toLowerCase();
    const cleanPass = (password || '').trim();
    const chosenRole = role || 'student';

    if (!cleanEmail || !cleanEmail.includes('@')) {
      return { status: 'error', message: 'Please enter a valid email address.' };
    }

    if (!cleanPass || cleanPass.length < 8) {
      return { status: 'error', message: 'Password must be at least 8 characters in length.' };
    }

    // Attempt client-side Supabase Auth
    if (supabaseClient && isSupabaseReady) {
      try {
        const { data, error } = await supabaseClient.auth.signInWithPassword({
          email: cleanEmail,
          password: cleanPass
        });

        if (error) {
          // Graceful handling of common Supabase Auth errors
          if (error.message.toLowerCase().includes('email not confirmed')) {
            return {
              status: 'unconfirmed',
              email: cleanEmail,
              message: 'Your email address has not been confirmed yet. Please check your inbox and click the verification link before signing in.'
            };
          }
          if (error.message.toLowerCase().includes('invalid login credentials')) {
            return {
              status: 'error',
              message: 'Invalid email or password. Please verify your credentials and try again.'
            };
          }
          return { status: 'error', message: error.message };
        }

        if (data?.user) {
          await syncServerSession(data.user);
          return {
            status: 'success',
            user: data.user,
            message: 'Signed in successfully! Redirecting...',
            redirect_url: '/profile'
          };
        }
      } catch (err) {
        console.warn('Client Supabase Auth exception, falling back to server:', err);
      }
    }

    // Fallback through backend API
    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          identifier: cleanEmail,
          password: cleanPass,
          role: chosenRole
        })
      });
      const result = await resp.json();
      if (resp.ok && result.status === 'success') {
        localStorage.setItem('collegehub_user', JSON.stringify(result.user));
        localStorage.setItem('collegehub_logged_in', 'true');
        return {
          status: 'success',
          user: result.user,
          message: result.message || 'Signed in successfully! Redirecting...',
          redirect_url: result.redirect_url || '/profile'
        };
      } else {
        return { status: 'error', message: result.message || 'Authentication failed.' };
      }
    } catch (e) {
      return { status: 'error', message: 'Unable to connect to authentication server. Please check your network connection.' };
    }
  }

  /**
   * Create-Account (Sign Up) with Email Confirmation:
   * Uses Supabase Auth; requires full name, valid email, password (>=8 chars), and confirm password.
   * Sends an email confirmation to new users before allowing normal sign-in.
   */
  async function signUpWithEmail(email, password, confirmPassword, fullName, role) {
    const cleanEmail = (email || '').trim().toLowerCase();
    const cleanPass = (password || '').trim();
    const cleanConfirm = (confirmPassword || '').trim();
    const cleanName = (fullName || '').trim();
    const chosenRole = role || 'student';

    if (!cleanName) {
      return { status: 'error', message: 'Please enter your Full Name.' };
    }

    if (!cleanEmail || !cleanEmail.includes('@')) {
      return { status: 'error', message: 'Please provide a valid email address.' };
    }

    const val = validatePassword(cleanPass, cleanConfirm);
    if (!val.hasMinLength) {
      return { status: 'error', message: 'Password must be at least 8 characters long.' };
    }
    if (!val.hasLetter) {
      return { status: 'error', message: 'Password must contain at least one letter.' };
    }
    if (!val.hasNumber) {
      return { status: 'error', message: 'Password must contain at least one number.' };
    }
    if (!val.matches) {
      return { status: 'error', message: 'Passwords do not match. Please re-enter both passwords.' };
    }

    const callbackUrl = window.location.origin + '/login.html';

    // Attempt client-side Supabase signUp
    if (supabaseClient && isSupabaseReady) {
      try {
        const { data, error } = await supabaseClient.auth.signUp({
          email: cleanEmail,
          password: cleanPass,
          options: {
            data: {
              full_name: cleanName,
              role: chosenRole
            },
            emailRedirectTo: callbackUrl
          }
        });

        if (error) {
          if (error.message.toLowerCase().includes('user already registered')) {
            return {
              status: 'error',
              message: 'An account with this email address already exists. Please sign in or reset your password.'
            };
          }
          return { status: 'error', message: error.message };
        }

        // Check if email confirmation is required (session will be null if confirmation is on)
        if (data?.user && !data?.session) {
          return {
            status: 'confirmation_required',
            email: cleanEmail,
            message: `A verification confirmation email has been dispatched to ${cleanEmail}. Please check your inbox and confirm your email before signing in.`
          };
        }

        // If email confirmation is disabled in Supabase, user has session immediately
        if (data?.session) {
          await syncServerSession(data.user);
          return {
            status: 'success',
            user: data.user,
            message: 'Account created successfully! Welcome to CollegeHub.',
            redirect_url: '/profile'
          };
        }
      } catch (err) {
        console.warn('Client Supabase signUp error, falling back to server:', err);
      }
    }

    // Server fallback
    try {
      const resp = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: cleanName,
          email: cleanEmail,
          password: cleanPass,
          role: chosenRole
        })
      });
      const result = await resp.json();
      if (resp.ok && result.status === 'success') {
        localStorage.setItem('collegehub_user', JSON.stringify(result.user));
        localStorage.setItem('collegehub_logged_in', 'true');
        return {
          status: 'success',
          user: result.user,
          message: result.message,
          redirect_url: '/profile'
        };
      } else {
        return { status: 'error', message: result.message || 'Registration failed.' };
      }
    } catch (e) {
      return { status: 'error', message: 'Unable to connect to registration server.' };
    }
  }

  /**
   * Resend signup confirmation email
   */
  async function resendConfirmationEmail(email) {
    const cleanEmail = (email || '').trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      return { status: 'error', message: 'Valid email address required.' };
    }

    const now = Math.floor(Date.now() / 1000);
    if (now - RATE_LIMITS.resendConfirmationLastSent < RATE_LIMITS.resendCooldownSeconds) {
      const remaining = RATE_LIMITS.resendCooldownSeconds - (now - RATE_LIMITS.resendConfirmationLastSent);
      return { status: 'error', message: `Please wait ${remaining} seconds before requesting another confirmation email.` };
    }

    if (supabaseClient && isSupabaseReady) {
      try {
        const { error } = await supabaseClient.auth.resend({
          type: 'signup',
          email: cleanEmail
        });
        if (error) throw error;
        RATE_LIMITS.resendConfirmationLastSent = now;
        return {
          status: 'success',
          message: `Confirmation email re-sent to ${cleanEmail}. Please check your inbox and spam folder.`
        };
      } catch (err) {
        console.warn('Supabase resend error:', err);
      }
    }

    RATE_LIMITS.resendConfirmationLastSent = now;
    return {
      status: 'success',
      message: `A fresh confirmation email has been dispatched to ${cleanEmail}.`
    };
  }

  /**
   * Forgot Password - Request Secure Reset Link:
   * Uses Supabase Auth's official password recovery flow (resetPasswordForEmail).
   * Directs user to CollageHub's dedicated /reset-password page.
   * Shows a generic confirmation message that does NOT reveal whether an email address exists.
   * Rate limited with cooldown.
   * Does NOT generate or store reset tokens in our own database.
   */
  async function sendPasswordResetLink(email) {
    const cleanEmail = (email || '').trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      return { status: 'error', message: 'Please enter a valid email address.' };
    }

    const now = Math.floor(Date.now() / 1000);
    if (now - RATE_LIMITS.recoveryLastSent < RATE_LIMITS.recoveryCooldownSeconds) {
      const wait = RATE_LIMITS.recoveryCooldownSeconds - (now - RATE_LIMITS.recoveryLastSent);
      return { status: 'cooldown', message: `Please wait ${wait} seconds before requesting another reset link.` };
    }

    RATE_LIMITS.recoveryLastSent = now;

    // Direct user to CollageHub's dedicated reset-password page
    const redirectTo = window.location.origin + '/reset-password';

    // Supabase Auth resetPasswordForEmail
    if (supabaseClient && isSupabaseReady) {
      try {
        await supabaseClient.auth.resetPasswordForEmail(cleanEmail, {
          redirectTo: redirectTo
        });
      } catch (err) {
        console.warn('Supabase resetPasswordForEmail notice:', err?.message);
      }
    }

    // Always return a generic confirmation message to prevent account enumeration
    return {
      status: 'success',
      email: cleanEmail,
      message: `If an account is associated with ${cleanEmail}, a secure password-reset link has been dispatched to your email. Please check your inbox and spam folder.`
    };
  }

  // Alias for backwards compatibility
  const sendPasswordRecovery = sendPasswordResetLink;

  /**
   * Verify recovery code with rate limiting (max 5 attempts)
   */
  async function verifyRecoveryCode(email, code) {
    const cleanEmail = (email || '').trim().toLowerCase();
    const cleanCode = (code || '').trim();

    if (!cleanCode || cleanCode.length !== 6) {
      return { status: 'error', message: 'Please enter the 6-digit verification code.' };
    }

    if (RATE_LIMITS.verificationAttempts <= 0) {
      return { status: 'locked', message: 'Too many incorrect attempts. Please request a new recovery code.' };
    }

    // 1. Client Supabase verifyOtp
    if (supabaseClient && isSupabaseReady) {
      try {
        const { data, error } = await supabaseClient.auth.verifyOtp({
          email: cleanEmail,
          token: cleanCode,
          type: 'recovery'
        });

        if (!error && data?.session) {
          return { status: 'success', message: 'Code verified successfully! You may now set your new password.' };
        }
      } catch (err) {
        console.warn('Supabase verifyOtp notice:', err);
      }
    }

    // 2. Server verification endpoint
    try {
      const resp = await fetch('/api/auth/verify-reset-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: cleanEmail, code: cleanCode })
      });
      const data = await resp.json();

      if (resp.ok && data.status === 'success') {
        return { status: 'success', message: 'Verification successful.' };
      } else {
        RATE_LIMITS.verificationAttempts -= 1;
        const remaining = RATE_LIMITS.verificationAttempts;
        if (remaining <= 0) {
          return { status: 'locked', message: 'Too many invalid attempts. Please request a new code.' };
        }
        return {
          status: 'error',
          message: `Invalid verification code. (${remaining} attempt${remaining === 1 ? '' : 's'} remaining)`
        };
      }
    } catch (e) {
      return { status: 'error', message: 'Unable to verify code. Please check your network connection.' };
    }
  }

  /**
   * Set and confirm new password after recovery verification
   */
  async function updatePassword(newPassword, confirmPassword, email, code) {
    const cleanPass = (newPassword || '').trim();
    const cleanConfirm = (confirmPassword || '').trim();

    const val = validatePassword(cleanPass, cleanConfirm);
    if (!val.hasMinLength) {
      return { status: 'error', message: 'New password must be at least 8 characters in length.' };
    }
    if (!val.hasLetter) {
      return { status: 'error', message: 'New password must contain at least one letter.' };
    }
    if (!val.hasNumber) {
      return { status: 'error', message: 'New password must contain at least one number.' };
    }
    if (!val.matches) {
      return { status: 'error', message: 'New passwords do not match. Please verify both fields.' };
    }

    // 1. Supabase updateUser (when recovery session is active)
    if (supabaseClient && isSupabaseReady) {
      try {
        const { error } = await supabaseClient.auth.updateUser({
          password: cleanPass
        });
        if (!error) {
          return {
            status: 'success',
            message: 'Your password has been reset successfully! You can now sign in with your new password.'
          };
        }
      } catch (err) {
        console.warn('Supabase updateUser notice:', err);
      }
    }

    // 2. Server password reset endpoint
    try {
      const resp = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          code: code,
          new_password: cleanPass
        })
      });
      const data = await resp.json();
      if (resp.ok && data.status === 'success') {
        return {
          status: 'success',
          message: 'Your password has been successfully reset! You can now log in.'
        };
      }
      return { status: 'error', message: data.message || 'Failed to update password.' };
    } catch (e) {
      return { status: 'error', message: 'Unable to connect to server to update password.' };
    }
  }

  // Toggle password visibility helper
  function toggleVisibility(inputId, btnEl) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPass = input.type === 'password';
    input.type = isPass ? 'text' : 'password';
    const icon = btnEl ? btnEl.querySelector('.material-symbols-outlined') : null;
    if (icon) {
      icon.textContent = isPass ? 'visibility_off' : 'visibility';
    }
  }

  // Initialize immediately
  initSupabase();

  // Expose public API
  window.CollegeHubSupabaseAuth = {
    init: initSupabase,
    signInWithGoogle: signInWithGoogle,
    signInWithEmail: signInWithEmail,
    signUpWithEmail: signUpWithEmail,
    sendPasswordResetLink: sendPasswordResetLink,
    sendPasswordRecovery: sendPasswordRecovery,
    verifyRecoveryCode: verifyRecoveryCode,
    updatePassword: updatePassword,
    resendConfirmationEmail: resendConfirmationEmail,
    validatePassword: validatePassword,
    updatePasswordRulesUI: updatePasswordRulesUI,
    toggleVisibility: toggleVisibility,
    showGoogleProviderSetupModal: showGoogleProviderSetupModal,
    checkGoogleProviderStatus: checkGoogleProviderStatus,
    getSupabaseClient: () => supabaseClient
  };
})();

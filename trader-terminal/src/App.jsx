import React, { useState, useEffect, useRef } from 'react';
import { I18nProvider, useTranslation } from './services/i18n.jsx';
import { apiService } from './services/api.js';

function MainApp() {
  const { lang, changeLanguage, t, locales, loading } = useTranslation();
  const [hash, setHash] = useState(() => window.location.hash || '#/');
  const [theme, setTheme] = useState(() => localStorage.getItem('yartrader_theme') || 'dark');
  const [token, setToken] = useState(() => localStorage.getItem('yartrader_token'));
  const [role, setRole] = useState(() => localStorage.getItem('yartrader_role'));
  const [name, setName] = useState(() => localStorage.getItem('yartrader_name'));

  // Notification state
  const [notif, setNotif] = useState({ show: false, msg: '', type: 'success' });

  // Dynamic state for data
  const [markets, setMarkets] = useState([]);
  const [signals, setSignals] = useState([]);
  const [compounding, setCompounding] = useState({
    simBalance: '10000',
    simYield: '8.5',
    simMonths: '6',
    initial: '$10,000',
    final: '$16,310',
    growth: '+63.1%'
  });
  const [subscriptionPlans, setSubscriptionPlans] = useState([]);
  const [blogArticles, setBlogArticles] = useState([]);
  const [publicMetrics, setPublicMetrics] = useState({
    activeMarketsCount: '30',
    historicalSimulatedTrades: '125k+',
    platformUptimePct: '99.9'
  });
  const [activeHorizon, setActiveHorizon] = useState('medium');
  const [selectedAsset, setSelectedAsset] = useState('all');

  // Execution Board states
  const [execPlans, setExecPlans] = useState([]);
  const [execConfidence, setExecConfidence] = useState({});
  const [execReasoning, setExecReasoning] = useState([]);
  const [structureMap, setStructureMap] = useState([]);
  const [structureAlignment, setStructureAlignment] = useState({});
  const [structureNarrative, setStructureNarrative] = useState('');
  const [liquidityMap, setLiquidityMap] = useState({});
  const [liquidityEvents, setLiquidityEvents] = useState([]);
  const [patternSimilarity, setPatternSimilarity] = useState({});
  const [portfolioRisk, setPortfolioRisk] = useState({});
  const [portfolioExposure, setPortfolioExposure] = useState([]);
  const [learningMatrix, setLearningMatrix] = useState([]);

  // SRE Admin panel states
  const [registerTf, setRegisterTf] = useState('64');
  const [adminSymbols, setAdminSymbols] = useState([]);
  const [adminReports, setAdminReports] = useState([]);
  const [devopsStatus, setDevopsStatus] = useState({});
  const [devopsMetrics, setDevopsMetrics] = useState({});
  const [validationHistory, setValidationHistory] = useState([]);
  const [validationStatus, setValidationStatus] = useState({});
  const [shadowMetrics, setShadowMetrics] = useState({});
  const [validationPhase, setValidationPhase] = useState('IDLE');
  const [validationComponent, setValidationComponent] = useState('N/A');
  const [validationTrace, setValidationTrace] = useState('N/A');
  const [validationLogs, setValidationLogs] = useState([]);

  // Auth Forms states
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPass, setLoginPass] = useState('');
  const [registerName, setRegisterName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPass, setRegisterPass] = useState('');
  const [forgotEmail, setForgotEmail] = useState('');

  // Floating Chatbot state
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([
    { text: "سلام! من دستیار هوشمند هوش شناختی بازار شما هستم. می‌توانید درباره الگوهای تاریخی، علل تصمیم‌گیری، اشتباهات یا دستاوردهای شناختی مغز معامله‌گر از من بپرسید.", sender: 'bot' }
  ]);
  const chatMessagesEndRef = useRef(null);

  // Sync hash state with window.location
  useEffect(() => {
    const handleHashChange = () => {
      const currentHash = window.location.hash || '#/';
      setHash(currentHash);
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Update body theme class
  useEffect(() => {
    if (theme === 'light') {
      document.body.classList.add('light-theme');
    } else {
      document.body.classList.remove('light-theme');
    }
  }, [theme]);

  // Dynamic Route Theme Mapping: Public pages -> Light editorial, Terminal/Admin -> Dark
  useEffect(() => {
    const savedTheme = localStorage.getItem('yartrader_theme');
    if (savedTheme) {
      setTheme(savedTheme);
    } else {
      const isPublic = hash === '#/' || hash === '#/features' || hash === '#/pricing' || hash === '#/blog' || hash === '#/login' || hash === '#/register' || hash === '#/forgot-password';
      if (isPublic) {
        setTheme('light');
      } else {
        setTheme('dark');
      }
    }
  }, [hash]);

  // Auth & Routing Guard
  useEffect(() => {
    // If attempting restricted routes without being logged in, redirect to login
    const isRestrictedRoute = hash === '#/dashboard' || hash === '#/execution-intel' || hash === '#/admin' || hash === '#/learning';
    if (isRestrictedRoute && !token) {
      window.location.hash = '#/login';
      showNotification(
        lang === 'fa' ? 'لطفا ابتدا وارد حساب خود شوید.' : 'Please sign in to access this zone.',
        'warning'
      );
    }
    // Admin specific guard
    if (hash === '#/admin' && token && role !== 'ADMIN') {
      showNotification(
        lang === 'fa' ? 'دسترسی فقط برای ادمین مجاز است.' : 'Admin role is required.',
        'warning'
      );
    }
  }, [hash, token, role]);

  // Route-specific Data Fetching
  useEffect(() => {
    if (hash === '#/' || hash === '') {
      fetchPublicMetrics();
    } else if (hash === '#/pricing') {
      fetchSubscriptionPlans();
    } else if (hash === '#/blog') {
      fetchBlogArticles();
    } else if (hash === '#/dashboard') {
      fetchUserSignals();
    } else if (hash === '#/execution-intel') {
      fetchExecutionIntelligence();
    } else if (hash === '#/learning') {
      fetchLearningMatrix();
    } else if (hash === '#/admin' && role === 'ADMIN') {
      fetchAdminSymbols();
      fetchAdminReports();
      fetchStatus();
    }
  }, [hash, selectedAsset, role, activeHorizon]);

  const showNotification = (msg, type = 'success') => {
    setNotif({ show: true, msg, type });
    setTimeout(() => {
      setNotif(prev => ({ ...prev, show: false }));
    }, 4000);
  };

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    localStorage.setItem('yartrader_theme', nextTheme);
  };

  // Auth Operations
  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await apiService.post('/api/auth/login', {
        email: loginEmail,
        password: loginPass
      });
      const tokenVal = res.session_token || res.token;
      const roleVal = (res.user && res.user.role) || res.role || 'USER';
      const nameVal = (res.user && res.user.name) || res.username || 'Elite Trader';

      localStorage.setItem('yartrader_token', tokenVal);
      localStorage.setItem('yartrader_role', roleVal);
      localStorage.setItem('yartrader_name', nameVal);
      setToken(tokenVal);
      setRole(roleVal);
      setName(nameVal);
      showNotification(lang === 'fa' ? 'ورود موفقیت‌آمیز بود.' : 'Successfully signed in.', 'success');
      window.location.hash = '#/dashboard';
    } catch (err) {
      showNotification(err.message, 'failed');
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await apiService.post('/api/auth/register', {
        name: registerName,
        username: registerName,
        email: registerEmail,
        password: registerPass
      });
      showNotification(
        lang === 'fa' ? 'ثبت‌نام با موفقیت انجام شد. لطفا وارد شوید.' : 'Successfully registered. Please login.',
        'success'
      );
      window.location.hash = '#/login';
    } catch (err) {
      showNotification(err.message, 'failed');
    }
  };

  const handleForgot = async (e) => {
    e.preventDefault();
    try {
      await apiService.post('/api/auth/forgot-password', { email: forgotEmail });
      showNotification(
        lang === 'fa' ? 'لینک بازیابی رمز عبور ارسال شد.' : 'Reset link has been sent.',
        'success'
      );
    } catch (err) {
      showNotification(err.message, 'failed');
    }
  };

  const handleLogout = async () => {
    try {
      const currentToken = localStorage.getItem('yartrader_token') || token || '';
      await apiService.post('/api/auth/logout', { token: currentToken });
    } catch (err) {
      console.warn("Logout endpoint error:", err);
    } finally {
      localStorage.removeItem('yartrader_token');
      localStorage.removeItem('yartrader_role');
      localStorage.removeItem('yartrader_name');
      setToken(null);
      setRole(null);
      setName(null);
      showNotification(lang === 'fa' ? 'با موفقیت خارج شدید.' : 'Successfully logged out.', 'success');
      window.location.hash = '#/';
    }
  };

  const handleSocialLogin = (provider) => {
    showNotification(
      lang === 'fa' ? `ورود با ${provider} شبیه‌سازی شد.` : `Signed in with ${provider} (Simulated).`,
      'success'
    );
    localStorage.setItem('yartrader_token', 'mock_social_token');
    localStorage.setItem('yartrader_role', 'ADMIN');
    localStorage.setItem('yartrader_name', `${provider} Guest`);
    setToken('mock_social_token');
    setRole('ADMIN');
    setName(`${provider} Guest`);
    window.location.hash = '#/dashboard';
  };

  // Data Fetching Operations
  const fetchPublicMetrics = async () => {
    try {
      const res = await apiService.get('/api/public/metrics');
      setPublicMetrics({
        activeMarketsCount: res.active_markets_count,
        historicalSimulatedTrades: res.historical_simulated_trades,
        platformUptimePct: res.platform_uptime_pct
      });
    } catch (err) {
      console.error("Error fetching public metrics:", err);
    }
  };

  const fetchSubscriptionPlans = async () => {
    try {
      const res = await apiService.get('/api/subscription/plans');
      setSubscriptionPlans(res);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchBlogArticles = async () => {
    try {
      const res = await apiService.get('/api/blog');
      setBlogArticles(res);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchUserSignals = async () => {
    try {
      const mkts = await apiService.get('/api/user/markets');
      setMarkets(mkts);
      const sigs = await apiService.get(`/api/user/signals?horizon=${activeHorizon}`);
      setSignals(sigs);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchLearningMatrix = async () => {
    try {
      const res = await apiService.get('/api/intelligence/learning-matrix');
      setLearningMatrix(res);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchExecutionIntelligence = async () => {
    try {
      const plans = await apiService.get('/api/execution/plans?symbol=XAUUSD&timeframe=H1');
      setExecPlans(plans);
      const conf = await apiService.get('/api/execution/confidence?symbol=XAUUSD&timeframe=H1');
      setExecConfidence(conf);
      const reas = await apiService.get('/api/execution/reasoning?symbol=XAUUSD&timeframe=H1');
      setExecReasoning(reas);
      const sMap = await apiService.get('/api/structure/map?symbol=XAUUSD&timeframe=H1');
      setStructureMap(sMap);
      const align = await apiService.get('/api/structure/alignment?symbol=XAUUSD');
      setStructureAlignment(align);
      const narr = await apiService.get('/api/structure/narrative?symbol=XAUUSD&timeframe=H1');
      setStructureNarrative(narr);
      const lMap = await apiService.get('/api/liquidity/map?symbol=XAUUSD&timeframe=H1');
      setLiquidityMap(lMap);
      const lEvents = await apiService.get('/api/liquidity/events?symbol=XAUUSD&timeframe=H1');
      setLiquidityEvents(lEvents);
      const sim = await apiService.get('/api/pattern/similarity?symbol=XAUUSD&timeframe=H1');
      setPatternSimilarity(sim);
      const risk = await apiService.get('/api/portfolio/risk');
      setPortfolioRisk(risk);
      const exp = await apiService.get('/api/portfolio/exposure');
      setPortfolioExposure(exp);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAdminSymbols = async () => {
    try {
      const currentToken = localStorage.getItem('yartrader_token') || token || '';
      const res = await apiService.get(`/api/admin/symbols?token=${encodeURIComponent(currentToken)}`);
      setAdminSymbols(res.registered_symbols || res.active_symbols || res || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAdminReports = async () => {
    try {
      const currentToken = localStorage.getItem('yartrader_token') || token || '';
      const res = await apiService.get(`/api/admin/reports?token=${encodeURIComponent(currentToken)}`);
      setAdminReports(res.reports || res || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchStatus = async () => {
    try {
      const devops = await apiService.get('/api/devops/status');
      setDevopsStatus(devops);
      const dMetrics = await apiService.get('/api/devops/metrics');
      setDevopsMetrics(dMetrics);
      const valHistory = await apiService.get('/api/validation/history');
      setValidationHistory(valHistory);
      const valStatus = await apiService.get('/api/validation/status');
      setValidationStatus(valStatus);
      const shadow = await apiService.get('/api/shadow/metrics');
      setShadowMetrics(shadow);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRegisterNewActiveSymbol = async () => {
    try {
      const currentToken = localStorage.getItem('yartrader_token') || token || '';
      const promptSymbol = prompt(lang === 'fa' ? 'لطفا نماد جدید را وارد کنید (مثلا SOLUSD):' : 'Enter new symbol (e.g. SOLUSD):', "XAUUSD");
      if (!promptSymbol) return;

      const res = await apiService.post(`/api/admin/symbols?token=${encodeURIComponent(currentToken)}`, {
        symbol: promptSymbol.toUpperCase(),
        timeframe: parseInt(registerTf),
        timeframes: ["H1"]
      });
      showNotification(res.message || "Symbol Registered.", "success");
      fetchAdminSymbols();
    } catch (err) {
      showNotification(err.message, "failed");
    }
  };

  // Compounding simulation
  const runCompoundingSimulation = () => {
    const bal = parseFloat(compounding.simBalance) || 0;
    const yld = parseFloat(compounding.simYield) || 0;
    const mths = parseInt(compounding.simMonths) || 0;

    let finalVal = bal;
    for (let i = 0; i < mths; i++) {
      finalVal = finalVal * (1 + yld / 100);
    }
    const growthPct = ((finalVal - bal) / bal) * 100;
    setCompounding(prev => ({
      ...prev,
      initial: `$${bal.toLocaleString()}`,
      final: `$${Math.round(finalVal).toLocaleString()}`,
      growth: `+${growthPct.toFixed(1)}%`
    }));
  };

  // Validation loop trigger
  const triggerValidation = async () => {
    try {
      await apiService.post('/api/validation/run', {});
      showNotification("SRE validation runner triggered.", "success");
      setValidationLogs([]);
      setValidationPhase('RUNNING');

      // Poll validation status
      let attempts = 0;
      const interval = setInterval(async () => {
        try {
          const status = await apiService.get('/api/validation/status');
          setValidationStatus(status);
          setValidationPhase(status.phase || 'IDLE');
          setValidationComponent(status.component || 'N/A');
          setValidationTrace(status.test || 'N/A');
          if (status.logs && status.logs.length > 0) {
            setValidationLogs(status.logs);
          }
          if (status.phase === 'SUCCESS' || status.phase === 'FAILED' || attempts > 20) {
            clearInterval(interval);
          }
        } catch (err) {
          clearInterval(interval);
        }
        attempts++;
      }, 1000);
    } catch (err) {
      showNotification(err.message, "failed");
    }
  };

  // Floating Chatbot triggers
  const toggleChatbot = () => {
    setChatOpen(prev => !prev);
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim()) return;
    const userMsg = chatInput;
    setChatMessages(prev => [...prev, { text: userMsg, sender: 'user' }]);
    setChatInput('');

    try {
      const res = await apiService.post('/api/chat/assistant', {
        question: userMsg,
        lang: lang
      });
      setChatMessages(prev => [...prev, { text: res.answer, sender: 'bot' }]);
    } catch (err) {
      setChatMessages(prev => [...prev, { text: `Error: ${err.message}`, sender: 'bot' }]);
    }
  };

  // Auto Scroll Chat
  useEffect(() => {
    chatMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, chatOpen]);

  const totalEvaluatedPatterns = learningMatrix.reduce((acc, curr) => acc + curr.sample_count, 0);
  const avgPatternWinRate = totalEvaluatedPatterns > 0
    ? (learningMatrix.reduce((acc, curr) => acc + (curr.win_rate_pct * curr.sample_count), 0) / totalEvaluatedPatterns).toFixed(1) + "%"
    : "0.0%";
  const avgRiskReward = totalEvaluatedPatterns > 0
    ? (learningMatrix.reduce((acc, curr) => acc + (curr.average_rr * curr.sample_count), 0) / totalEvaluatedPatterns).toFixed(1) + " R"
    : "0.0 R";

  return (
    <div>
      {/* Dynamic Toast/Notification Overlay */}
      {notif.show && (
        <div className={`notification ${notif.type}`} style={{ display: 'block' }}>
          {notif.msg}
        </div>
      )}

      {/* Global Header */}
      <div className="header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <span style={{ fontSize: '1.4em', fontWeight: 'bold', color: 'var(--primary)', letterSpacing: '1px' }}>
            YarTrader
          </span>
          <span id="uptime-indicator" className="status-item state-online" style={{ fontSize: '0.8em', padding: '6px 12px', border: 'none' }}>
            {t('online')}
          </span>
          <span id="portal-status-label" style={{ fontSize: '0.85em', color: 'var(--text-muted)' }}>
            {t('portal_status')}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          {/* Theme Switcher */}
          <button className="btn" onClick={toggleTheme} title={t('theme_toggle')}>
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>

          {/* Bilingual Selector */}
          <select
            className="select-field"
            id="lang-select"
            value={lang}
            onChange={(e) => changeLanguage(e.target.value)}
            style={{ width: '120px', padding: '6px' }}
          >
            <option value="fa">فارسی</option>
            <option value="en">English</option>
            <option value="tr">Türkçe</option>
            <option value="ar">العربية</option>
          </select>
        </div>
      </div>

      {/* Main Container Layout */}
      <div className="container">
        {/* Navigation Sidebar */}
        <div className="sidebar">
          <a href="#/" className={`sidebar-link ${hash === '#/' ? 'active' : ''}`}>{t('nav_public')}</a>
          <a href="#/features" className={`sidebar-link ${hash === '#/features' ? 'active' : ''}`}>{t('nav_features')}</a>
          <a href="#/pricing" className={`sidebar-link ${hash === '#/pricing' ? 'active' : ''}`}>{t('nav_pricing')}</a>
          <a href="#/blog" className={`sidebar-link ${hash === '#/blog' ? 'active' : ''}`}>{t('nav_blog')}</a>
          {token && <a href="#/dashboard" className={`sidebar-link ${hash === '#/dashboard' ? 'active' : ''}`}>{t('nav_terminal')}</a>}
          {token && <a href="#/execution-intel" className={`sidebar-link ${hash === '#/execution-intel' ? 'active' : ''}`}>{t('nav_execution_intel')}</a>}
          {token && <a href="#/learning" className={`sidebar-link ${hash === '#/learning' ? 'active' : ''}`}>{t('nav_learning') || '🧠 Learning Matrix'}</a>}
          {token && role === 'ADMIN' && <a href="#/admin" className={`sidebar-link ${hash === '#/admin' ? 'active' : ''}`}>{t('nav_admin')}</a>}

          <div style={{ marginTop: 'auto', borderTop: '1px solid var(--border-dark)', paddingTop: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {token && (
              <div id="user-profile-badge" style={{ display: 'block', padding: '10px', backgroundColor: 'rgba(79, 70, 229, 0.1)', borderRadius: '6px', fontWeight: 'bold', textAlign: 'center', color: 'var(--primary)' }}>
                {name} ({role})
              </div>
            )}
            {!token && <a href="#/login" className={`sidebar-link ${hash === '#/login' ? 'active' : ''}`}>{t('nav_login')}</a>}
            {!token && <a href="#/register" className={`sidebar-link ${hash === '#/register' ? 'active' : ''}`}>{t('nav_register')}</a>}
            {token && (
              <a href="javascript:void(0)" className="sidebar-link" onClick={handleLogout}>
                {t('nav_logout')}
              </a>
            )}
          </div>
        </div>

        {/* Multi-Shell Main Panel Router */}
        <div className="main-panel">
          {/* PANEL 1: PUBLIC MARKETING LANDING SHELL */}
          {hash === '#/' && (
            <div id="shell-marketing">
              <div className="card" style={{ borderRight: '6px solid var(--accent)', borderLeft: '6px solid var(--accent)' }}>
                <h2 style={{ margin: '0 0 10px 0', color: 'var(--primary)' }}>{t('welcome_title')}</h2>
                <p style={{ fontSize: '1.05em', lineHeight: '1.7' }}>
                  {t('welcome_desc')}
                </p>

                <div className="status-board" style={{ marginTop: '25px' }}>
                  <div className="status-item">
                    <div>{t('pub_markets_title')}</div>
                    <div id="pub-markets" className="status-val status-passed">{publicMetrics.activeMarketsCount}</div>
                  </div>
                  <div className="status-item">
                    <div>{t('pub_trades_title')}</div>
                    <div id="pub-trades" className="status-val" style={{ color: 'var(--primary)' }}>
                      {typeof publicMetrics.historicalSimulatedTrades === 'number'
                        ? (publicMetrics.historicalSimulatedTrades / 1000).toFixed(1) + 'k+'
                        : publicMetrics.historicalSimulatedTrades}
                    </div>
                  </div>
                  <div className="status-item">
                    <div>{t('pub_uptime_title')}</div>
                    <div id="pub-uptime" className="status-val status-passed">
                      {typeof publicMetrics.platformUptimePct === 'number'
                        ? publicMetrics.platformUptimePct + '%'
                        : publicMetrics.platformUptimePct}
                    </div>
                  </div>
                  <div className="status-item">
                    <div>{t('pub_standards_title')}</div>
                    <div className="status-val status-warn" style={{ fontSize: '1.1em', fontWeight: 'bold' }}>{t('pes_compliant')}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* PANEL 1B: FEATURES */}
          {hash === '#/features' && (
            <div id="shell-features">
              <div className="card">
                <h2 style={{ marginTop: 0, color: 'var(--primary)' }}>{t('features_title') || 'YarTrader Cognitive Features'}</h2>
                <p style={{ color: 'var(--text-muted)', marginBottom: '25px' }}>{t('features_desc') || 'Discover our multi-layered cognitive intelligence architecture.'}</p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px' }}>
                  <div className="status-item" style={{ textAlign: 'inherit', padding: '20px' }}>
                    <h3 style={{ color: 'var(--primary)', marginTop: 0 }}>{t('feature_1_title') || 'No Technical Indicators'}</h3>
                    <p style={{ fontSize: '0.9em', lineHeight: '1.6', color: 'var(--text-muted)' }}>{t('feature_1_desc') || 'Complete elimination of subjective lagging indicators.'}</p>
                  </div>
                  <div className="status-item" style={{ textAlign: 'inherit', padding: '20px' }}>
                    <h3 style={{ color: 'var(--primary)', marginTop: 0 }}>{t('feature_2_title') || 'Multi-Horizon Alignment'}</h3>
                    <p style={{ fontSize: '0.9em', lineHeight: '1.6', color: 'var(--text-muted)' }}>{t('feature_2_desc') || 'Chronological multi-timeframe decision fusion logic.'}</p>
                  </div>
                  <div className="status-item" style={{ textAlign: 'inherit', padding: '20px' }}>
                    <h3 style={{ color: 'var(--primary)', marginTop: 0 }}>{t('feature_3_title') || 'Virtual Position Tracker'}</h3>
                    <p style={{ fontSize: '0.9em', lineHeight: '1.6', color: 'var(--text-muted)' }}>{t('feature_3_desc') || 'The cognitive simulated Shadow Trading Engine.'}</p>
                  </div>
                  <div className="status-item" style={{ textAlign: 'inherit', padding: '20px' }}>
                    <h3 style={{ color: 'var(--primary)', marginTop: 0 }}>{t('feature_4_title') || 'Active Learning Loop'}</h3>
                    <p style={{ fontSize: '0.9em', lineHeight: '1.6', color: 'var(--text-muted)' }}>{t('feature_4_desc') || 'Four-layered memory system.'}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* PANEL 1C: PRICING */}
          {hash === '#/pricing' && (
            <div id="shell-pricing">
              <div className="card">
                <h2 style={{ marginTop: 0, color: 'var(--primary)' }}>{t('pricing_title')}</h2>
                <p style={{ color: 'var(--text-muted)', marginBottom: '25px' }}>{t('pricing_desc')}</p>

                <div className="blog-grid" id="pricing-plans-container">
                  {subscriptionPlans.map((plan, idx) => (
                    <div key={idx} className="status-item" style={{ textAlign: 'inherit', padding: '20px', borderTop: '4px solid var(--primary)' }}>
                      <h3 style={{ color: 'var(--primary)', marginTop: 0 }}>{plan.name}</h3>
                      <div className="status-val" style={{ fontSize: '1.5em', margin: '10px 0', color: 'var(--text-dark)' }}>{plan.price_usd || plan.price}</div>
                      <p style={{ fontSize: '0.9em', color: 'var(--text-muted)', lineHeight: '1.6' }}>
                        {plan.description || `Max Active Symbols: ${plan.max_symbols} | Timeframes: ${plan.enabled_timeframes?.join(', ')}`}
                      </p>
                      <ul style={{ paddingLeft: '15px', fontSize: '0.85em', color: 'var(--text-muted)', lineHeight: '1.7', marginTop: '15px' }}>
                        {plan.features?.map((f, fIdx) => <li key={fIdx}>{f}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* PANEL 1D: RESEARCH BLOG */}
          {hash === '#/blog' && (
            <div id="shell-blog">
              <div className="card">
                <h2 style={{ marginTop: 0, color: 'var(--primary)' }}>{t('nav_blog')}</h2>
                <div className="blog-grid">
                  {blogArticles.map((art, idx) => (
                    <div key={idx} className="status-item" style={{ textAlign: 'inherit', padding: '20px', borderLeft: '4px solid var(--primary)' }}>
                      <h3 style={{ color: 'var(--primary)', marginTop: 0 }}>{art.title}</h3>
                      <div style={{ fontSize: '0.8em', color: 'var(--text-muted)', marginBottom: '10px' }}>
                        {art.date} | By {art.author}
                      </div>
                      <p style={{ fontSize: '0.9em', lineHeight: '1.6' }}>{art.summary}</p>
                      <div style={{ marginTop: '15px' }}>
                        {art.tags?.map((tag, tIdx) => (
                          <span key={tIdx} style={{ fontSize: '0.75em', padding: '4px 8px', background: 'rgba(79, 70, 229, 0.1)', color: 'var(--primary)', borderRadius: '4px', marginRight: '5px' }}>
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* PANEL 2: CUSTOMER FINANCIAL TERMINAL SHELL */}
          {hash === '#/dashboard' && (
            <div id="shell-terminal">
              <div className="card">
                <h2 style={{ marginTop: 0, color: 'var(--primary)' }}>{t('terminal_title')}</h2>
                <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>{t('terminal_desc')}</p>

                {/* Horizons tabs and Asset selector */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '15px', marginBottom: '25px', backgroundColor: 'rgba(30, 41, 59, 0.3)', padding: '12px', borderRadius: '12px', border: '1px solid var(--border-dark)', alignItems: 'center' }}>
                  {['micro', 'short', 'medium', 'macro'].map((hType) => (
                    <button
                      key={hType}
                      className="btn"
                      style={{
                        flex: 1,
                        padding: '10px',
                        backgroundColor: activeHorizon === hType ? 'var(--primary)' : 'transparent',
                        color: activeHorizon === hType ? 'white' : 'var(--text-muted)'
                      }}
                      onClick={() => setActiveHorizon(hType)}
                    >
                      {hType === 'micro' && `⚡ ${t('horizon_micro') || 'Micro'}`}
                      {hType === 'short' && `📊 ${t('horizon_short') || 'Short'}`}
                      {hType === 'medium' && `📈 ${t('horizon_medium') || 'Medium'}`}
                      {hType === 'macro' && `💎 ${t('horizon_macro') || 'Macro'}`}
                    </button>
                  ))}

                  <select
                    className="select-field"
                    value={selectedAsset}
                    onChange={(e) => setSelectedAsset(e.target.value)}
                    style={{ minWidth: '150px' }}
                  >
                    <option value="all">🌐 All Assets</option>
                    <option value="gold">🏆 XAUUSD (Gold)</option>
                    <option value="bitcoin">₿ BTCUSD (Bitcoin)</option>
                    <option value="euro">💶 EURUSD (Euro)</option>
                  </select>
                </div>

                {/* Signals Feed Grid */}
                <div className="blog-grid">
                  {signals && signals.length > 0 ? (
                    signals
                      .filter(s => {
                        if (selectedAsset === 'all') return true;
                        const sym = s.symbol ? s.symbol.toUpperCase() : '';
                        if (selectedAsset === 'gold' && sym.includes('XAU')) return true;
                        if (selectedAsset === 'bitcoin' && (sym.includes('BTC') || sym.includes('BITCOIN'))) return true;
                        if (selectedAsset === 'euro' && sym.includes('EUR')) return true;
                        return s.symbol_class === selectedAsset;
                      })
                      .map((sig, idx) => {
                        const posture = sig.posture || (sig.direction === 'BUY' || sig.direction === 'Bullish' || sig.direction === 'BULLISH' ? 'BULLISH' : 'BEARISH');
                        const isBullish = posture === 'BULLISH' || posture === 'BUY';
                        const narrativeText = sig.narrative || sig.reason || sig.explanation || 'No setup description.';
                        return (
                          <div key={idx} className="status-item" style={{ textAlign: 'inherit', padding: '20px', borderRight: `4px solid ${isBullish ? 'var(--accent)' : 'var(--danger)'}` }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                              <span style={{ fontWeight: 'bold', color: 'var(--text-dark)' }}>{sig.symbol}</span>
                              <span className={`status-val ${isBullish ? 'status-passed' : 'status-failed'}`} style={{ fontSize: '0.85em', padding: '2px 8px', borderRadius: '4px' }}>
                                {posture}
                              </span>
                            </div>
                            <div style={{ fontSize: '0.8em', color: 'var(--text-muted)', marginBottom: '10px' }}>
                              Frame: {sig.timeframe || 'H1'} | Confidence: {sig.confidence}%
                            </div>
                            {sig.entry_zone && (
                              <div style={{ fontSize: '0.85em', margin: '4px 0' }}>
                                <strong>Entry:</strong> {sig.entry_zone}
                              </div>
                            )}
                            {sig.target_zone && (
                              <div style={{ fontSize: '0.85em', margin: '4px 0' }}>
                                <strong>Target:</strong> {sig.target_zone}
                              </div>
                            )}
                            {sig.invalidation_level && (
                              <div style={{ fontSize: '0.85em', margin: '4px 0' }}>
                                <strong>Invalidation:</strong> {sig.invalidation_level}
                              </div>
                            )}
                            <p style={{ fontSize: '0.85em', marginTop: '10px', color: 'var(--text-dark)', borderTop: '1px solid var(--border-dark)', paddingTop: '8px' }}>
                              {narrativeText}
                            </p>
                          </div>
                        );
                      })
                  ) : (
                    <div style={{ gridColumn: 'span 3', padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No signals active for this horizon. Try triggering validation or adding predictive shadow orders!
                    </div>
                  )}
                </div>
              </div>

              {/* Equity Growth simulator */}
              <div className="card">
                <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>{t('compounding_title')}</h3>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '20px' }}>
                  <div className="form-group">
                    <label className="form-label">{t('compounding_initial')}</label>
                    <input className="input-field" type="number" value={compounding.simBalance} onChange={(e) => setCompounding({ ...compounding, simBalance: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Monthly Growth %</label>
                    <input className="input-field" type="number" value={compounding.simYield} onChange={(e) => setCompounding({ ...compounding, simYield: e.target.value })} step="0.1" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Months Duration</label>
                    <input className="input-field" type="number" value={compounding.simMonths} onChange={(e) => setCompounding({ ...compounding, simMonths: e.target.value })} />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: '18px' }}>
                    <button className="btn" style={{ width: '100%' }} onClick={runCompoundingSimulation}>{t('simulate_btn')}</button>
                  </div>
                </div>

                <div className="status-board">
                  <div className="status-item">
                    <div>{t('compounding_initial')}</div>
                    <div className="status-val" style={{ color: 'var(--text-dark)' }}>{compounding.initial}</div>
                  </div>
                  <div className="status-item">
                    <div>{t('compounding_projected')}</div>
                    <div className="status-val status-passed">{compounding.final}</div>
                  </div>
                  <div className="status-item">
                    <div>{t('compounding_yield')}</div>
                    <div className="status-val status-passed">{compounding.growth}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* PANEL 2B: EXECUTION INTELLIGENCE ZONE */}
          {hash === '#/execution-intel' && (
            <div id="shell-execution-intel">
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px', marginBottom: '25px' }}>
                <div className="card">
                  <h2 style={{ marginTop: 0, color: 'var(--primary)' }}>🎯 Institutional Execution Board</h2>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9em', marginBottom: '20px' }}>
                    Advisory trade plans formulated based on chronological market structure alignment. Zero automated execution.
                  </p>
                  <div className="status-board" style={{ marginBottom: '20px' }}>
                    <div className="status-item">
                      <div>Action</div>
                      <div className="status-val" style={{ color: 'var(--accent)' }}>
                        {execPlans[0]?.action || 'WAIT'}
                      </div>
                    </div>
                    <div className="status-item">
                      <div>Advisory Entry</div>
                      <div className="status-val" style={{ color: 'var(--text-dark)', fontFamily: 'monospace' }}>
                        {execPlans[0]?.entry_price || '-'}
                      </div>
                    </div>
                    <div className="status-item">
                      <div>Stop Loss</div>
                      <div className="status-val" style={{ color: 'var(--danger)', fontFamily: 'monospace' }}>
                        {execPlans[0]?.stop_loss || '-'}
                      </div>
                    </div>
                    <div className="status-item">
                      <div>Take Profit</div>
                      <div className="status-val" style={{ color: 'var(--accent)', fontFamily: 'monospace' }}>
                        {execPlans[0]?.take_profit || '-'}
                      </div>
                    </div>
                    <div className="status-item">
                      <div>Risk/Reward</div>
                      <div className="status-val" style={{ color: 'var(--primary)', fontFamily: 'monospace' }}>
                        {execPlans[0]?.risk_reward || '-'}
                      </div>
                    </div>
                    <div className="status-item">
                      <div>Confidence</div>
                      <div className="status-val" style={{ color: 'var(--warning)', fontFamily: 'monospace' }}>
                        {execConfidence.confidence || '-'}
                      </div>
                    </div>
                  </div>

                  <h4 style={{ color: 'var(--primary)', margin: '0 0 10px 0' }}>Reasoning Trace (XAI)</h4>
                  <ul style={{ lineHeight: '1.6', paddingLeft: '20px', color: 'var(--text-muted)' }}>
                    {execReasoning.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                </div>

                <div className="card">
                  <h2 style={{ marginTop: 0, color: 'var(--primary)' }}>🛡️ Portfolio Risk Board</h2>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9em', marginBottom: '20px' }}>
                    Enforces risk controls on asset concentration and correlation heat.
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginBottom: '20px' }}>
                    <div className="status-item">
                      <div>Portfolio Heat</div>
                      <div className="status-val" style={{ color: 'var(--danger)', fontFamily: 'monospace' }}>
                        {portfolioRisk.portfolio_heat || '0%'}
                      </div>
                    </div>
                    <div className="status-item">
                      <div>Risk Budget Left</div>
                      <div className="status-val" style={{ color: 'var(--accent)', fontFamily: 'monospace' }}>
                        {portfolioRisk.risk_budget_remaining || '100%'}
                      </div>
                    </div>
                    <div className="status-item">
                      <div>Drawdown Risk</div>
                      <div className="status-val" style={{ color: 'var(--warning)' }}>
                        {portfolioRisk.drawdown_level || 'LOW'}
                      </div>
                    </div>
                    <div className="status-item">
                      <div>SRE Risk Approved</div>
                      <div className="status-val status-passed">
                        {portfolioRisk.risk_approved ? 'APPROVED' : 'BLOCKED'}
                      </div>
                    </div>
                  </div>

                  <h4 style={{ color: 'var(--primary)', margin: '0 0 10px 0' }}>Portfolio Exposure & Concentration</h4>
                  <ul style={{ lineHeight: '1.6', paddingLeft: '20px', color: 'var(--text-muted)' }}>
                    {portfolioExposure.map((exp, idx) => (
                      <li key={idx}>{exp.asset}: {exp.percentage}%</li>
                    ))}
                  </ul>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '25px' }}>
                <div className="card">
                  <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>📈 Market Structure Map (Pure Price Action)</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85em', marginBottom: '15px' }}>
                    Tracks Swing Highs and Lows chronologically. Zero technical indicators are used.
                  </p>
                  <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                    <table>
                      <thead>
                        <tr>
                          <th>Bar Node</th>
                          <th>Price</th>
                          <th>Type</th>
                          <th>Structural Label</th>
                        </tr>
                      </thead>
                      <tbody>
                        {structureMap.map((node, idx) => (
                          <tr key={idx}>
                            <td>{node.node_index}</td>
                            <td>{node.price}</td>
                            <td>{node.type}</td>
                            <td>{node.label}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="card">
                  <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>🧱 Institutional Supply/Demand Zones</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85em', marginBottom: '15px' }}>
                    Identifies Order Blocks and Fair Value Gaps (FVG) with freshness metrics.
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                    <div>
                      <h4 style={{ color: 'var(--primary)', margin: '0 0 10px 0' }}>Order Blocks (OB)</h4>
                      <div>
                        {liquidityMap.order_blocks?.map((ob, idx) => (
                          <div key={idx} className="status-item" style={{ marginBottom: '8px' }}>
                            <div>Price: {ob.price}</div>
                            <div>Strength: {ob.strength}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h4 style={{ color: 'var(--warning)', margin: '0 0 10px 0' }}>Fair Value Gaps (FVG)</h4>
                      <div>
                        {liquidityMap.fair_value_gaps?.map((fvg, idx) => (
                          <div key={idx} className="status-item" style={{ marginBottom: '8px' }}>
                            <div>Gap: {fvg.low} - {fvg.high}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div className="card">
                  <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>🌐 Multi-Timeframe Structural Alignment</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85em', marginBottom: '20px' }}>
                    Synthesizes trend alignment from higher timeframes (D1/H4) down to the execution frame.
                  </p>
                  <div className="status-board" style={{ marginBottom: '15px' }}>
                    <div className="status-item">
                      <div>Alignment Status</div>
                      <div className="status-val" style={{ color: 'var(--accent)', fontSize: '1.1em' }}>
                        {structureAlignment.alignment_state || 'FULLY_ALIGNED'}
                      </div>
                    </div>
                    <div className="status-item">
                      <div>Synthesis Confidence</div>
                      <div className="status-val" style={{ color: 'var(--warning)' }}>
                        {structureAlignment.synthesis_confidence || '88'}%
                      </div>
                    </div>
                  </div>
                  <div style={{ padding: '12px', background: 'rgba(30, 41, 59, 0.4)', border: '1px solid var(--border-dark)', borderRadius: '8px', color: 'var(--text-dark)', lineHeight: '1.5' }}>
                    {structureNarrative || 'No structural narrative available.'}
                  </div>
                </div>

                <div className="card">
                  <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>🧠 Pattern Similarity Intelligence Feed</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85em', marginBottom: '20px' }}>
                    Matches the current market structure signature with the 4-layered memory system.
                  </p>

                  <div style={{ background: 'rgba(30, 41, 59, 0.2)', border: '1px solid var(--border-dark)', borderRadius: '10px', padding: '18px' }}>
                    <div style={{ marginBottom: '10px' }}><strong>Matched Pattern ID:</strong> <span style={{ color: 'var(--accent)', fontFamily: 'monospace' }}>{patternSimilarity.pattern_id || '-'}</span></div>
                    <div style={{ marginBottom: '10px' }}><strong>Cosine Similarity Score:</strong> <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>{patternSimilarity.similarity_score || '-'}</span></div>
                    <div style={{ marginBottom: '10px' }}><strong>Historical Occurrences:</strong> <span style={{ color: 'var(--warning)', fontWeight: 'bold' }}>{patternSimilarity.occurrences || '-'}</span></div>
                    <div style={{ marginBottom: '10px' }}><strong>Historical Success Rate:</strong> <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>{patternSimilarity.success_rate || '-'}</span></div>
                    <div style={{ marginTop: '15px', borderTop: '1px solid var(--border-dark)', paddingTop: '10px', fontStyle: 'italic', color: 'var(--text-muted)' }}>
                      {patternSimilarity.description || 'No matching similarities at this timeframe.'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* PANEL 2C: MULTI-TIMEFRAME LEARNING MATRIX SHELL */}
          {hash === '#/learning' && (
            <div id="shell-learning">
              {/* Scoreboard Cards */}
              <div className="card">
                <h2 style={{ marginTop: 0, color: 'var(--primary)' }}>🧠 Multi-Timeframe Market Brain Learning Engine</h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.95em', marginBottom: '25px' }}>
                  Continuously processes, categorizes, and evaluates market pattern sequences across the 9-timeframe matrix: <strong>Tick..MN1</strong>.
                </p>

                <div className="status-board">
                  <div className="status-item">
                    <div>Total Evaluated Patterns</div>
                    <div className="status-val" style={{ color: 'var(--primary)' }}>{totalEvaluatedPatterns}</div>
                  </div>
                  <div className="status-item">
                    <div>Avg Pattern Win-Rate</div>
                    <div className="status-val status-passed">
                      {avgPatternWinRate}
                    </div>
                  </div>
                  <div className="status-item">
                    <div>Average Risk/Reward (R:R)</div>
                    <div className="status-val" style={{ color: 'var(--accent)', fontFamily: 'monospace' }}>
                      {avgRiskReward}
                    </div>
                  </div>
                  <div className="status-item">
                    <div>Cognitive Confidence Shift</div>
                    <div className="status-val status-warn" style={{ fontSize: '1.1em', fontWeight: 'bold' }}>
                      STATISTICAL_GATES
                    </div>
                  </div>
                </div>
              </div>

              {/* Performance Table */}
              <div className="card">
                <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>📈 Multi-Timeframe Pattern Performance Table</h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85em', marginBottom: '15px' }}>
                  Reflecting the 9-timeframe context pattern database with historical sample size validation gates.
                </p>
                <div style={{ overflowX: 'auto' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Pattern Key</th>
                        <th>Pattern Name</th>
                        <th>Sample Count (N)</th>
                        <th>Win Rate</th>
                        <th>Avg R:R achieved</th>
                        <th>Avg MAE</th>
                        <th>Avg MFE</th>
                        <th>Active Multiplier</th>
                      </tr>
                    </thead>
                    <tbody>
                      {learningMatrix.map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontFamily: 'monospace', fontSize: '0.85em', color: 'var(--text-muted)' }}>{item.pattern_key}</td>
                          <td><strong>{item.pattern_name}</strong></td>
                          <td>{item.sample_count}</td>
                          <td>
                            <strong className={item.win_rate_pct >= 50 ? "status-passed" : "status-failed"}>
                              {item.win_rate_pct}%
                            </strong>
                          </td>
                          <td>{item.average_rr} R</td>
                          <td>{item.average_mae}</td>
                          <td>{item.average_mfe}</td>
                          <td>
                            <span className="blog-tag" style={{ background: item.active_confidence_multiplier >= 1.0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)' }}>
                              x{item.active_confidence_multiplier}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Distribution metrics & Historical Accuracy trends & Failure Pattern Logs */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                {/* M5/M15 Win-rate & R:R distribution metrics */}
                <div className="card">
                  <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>📊 M5/M15 Win-Rate & R:R Distribution Metrics</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85em', marginBottom: '20px' }}>
                    Distribution of execution metrics for low-timeframe execution and setups.
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                    <div className="status-item" style={{ textAlign: 'left' }}>
                      <strong>M5 Primary Execution Horizon</strong>
                      <div style={{ height: '8px', background: 'var(--border-dark)', borderRadius: '4px', marginTop: '8px', overflow: 'hidden' }}>
                        <div style={{ width: '66.7%', height: '100%', background: 'var(--accent)' }}></div>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8em', color: 'var(--text-muted)', marginTop: '5px' }}>
                        <span>Win-rate: 66.7%</span>
                        <span>Avg R:R: 2.5 R</span>
                      </div>
                    </div>

                    <div className="status-item" style={{ textAlign: 'left' }}>
                      <strong>M15 Primary Decision Horizon</strong>
                      <div style={{ height: '8px', background: 'var(--border-dark)', borderRadius: '4px', marginTop: '8px', overflow: 'hidden' }}>
                        <div style={{ width: '100.0%', height: '100%', background: 'var(--primary)' }}></div>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8em', color: 'var(--text-muted)', marginTop: '5px' }}>
                        <span>Win-rate: 100.0%</span>
                        <span>Avg R:R: 3.1 R</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Historical Accuracy Trends & Failure Pattern Logs */}
                <div className="card">
                  <h3 style={{ marginTop: 0, color: 'var(--warning)' }}>⚠️ Failure Pattern Logs & Accuracy Trends</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85em', marginBottom: '20px' }}>
                    Lists patterns reporting high failure rates requiring research focus or active avoidance.
                  </p>

                  <div style={{ overflowY: 'auto', maxHeight: '180px' }}>
                    {learningMatrix.filter(item => item.win_rate_pct < 50.0).length === 0 ? (
                      <div style={{ padding: '15px', color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center' }}>
                        No failure patterns currently logged (Win-rates &gt;= 50%).
                      </div>
                    ) : (
                      learningMatrix.filter(item => item.win_rate_pct < 50.0).map((item, idx) => (
                        <div key={idx} className="status-item" style={{ textAlign: 'left', borderLeft: '4px solid var(--danger)', marginBottom: '10px' }}>
                          <strong>{item.pattern_name}</strong> (N={item.sample_count})
                          <br/><small style={{ color: 'var(--text-muted)' }}>Key: {item.pattern_key} | Win-rate: {item.win_rate_pct}%</small>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* PANEL 3: INTERNAL SRE ADMIN CONTROL CENTER SHELL */}
          {hash === '#/admin' && role === 'ADMIN' && (
            <div id="shell-admin">
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px', flexWrap: 'wrap', gap: '15px' }}>
                  <h2 style={{ color: 'var(--primary)', margin: 0 }}>{t('admin_title')}</h2>

                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <select className="select-field" value={registerTf} onChange={(e) => setRegisterTf(e.target.value)}>
                      <option value="1">1 Tick Frame (Micro)</option>
                      <option value="4">4 Tick Frame (Short)</option>
                      <option value="16">16 Tick Frame (Medium)</option>
                      <option value="64">64 Tick Frame (Medium-High)</option>
                      <option value="256">256 Tick Frame (Macro)</option>
                      <option value="1024">1024 Tick Frame (Super Macro)</option>
                    </select>
                    <button className="btn" style={{ backgroundColor: 'var(--accent)', fontSize: '0.9em', padding: '10px 18px' }} onClick={handleRegisterNewActiveSymbol}>
                      {t('admin_add_symbol')}
                    </button>
                  </div>
                </div>

                <div className="status-board">
                  <div className="status-item">
                    <div>{t('admin_active_symbols')}</div>
                    <div className="status-val status-passed">{adminSymbols.length} / 30</div>
                  </div>
                  <div className="status-item">
                    <div>{t('admin_limits')}</div>
                    <div className="status-val status-passed" style={{ fontSize: '1.1em', fontWeight: 'bold' }}>{t('admin_limit_enforced')}</div>
                  </div>
                </div>

                <p style={{ marginTop: '15px', lineHeight: '1.6' }}>
                  <strong style={{ marginRight: '10px' }}>{t('admin_symbols_list')}</strong>
                  <span style={{ color: 'var(--primary)', fontFamily: 'monospace' }}>
                    {adminSymbols.map(s => s.symbol).join(', ') || 'None'}
                  </span>
                </p>
              </div>

              {/* SRE Validation Hub */}
              <div className="card">
                <h2>{t('validation_center_title')}</h2>
                <div className="status-board">
                  <div className="status-item">
                    <div>{t('passed_label')}</div>
                    <div className="status-val status-passed">{validationStatus.passed || 0}</div>
                  </div>
                  <div className="status-item">
                    <div>{t('failed_label')}</div>
                    <div className="status-val status-failed">{validationStatus.failed || 0}</div>
                  </div>
                  <div className="status-item">
                    <div>{t('skipped_label')}</div>
                    <div className="status-val">{validationStatus.skipped || 0}</div>
                  </div>
                  <div className="status-item">
                    <div>{t('warnings_label')}</div>
                    <div className="status-val status-warn">{validationStatus.warnings || 0}</div>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px', marginTop: '20px' }}>
                  <div>
                    <button className="btn" style={{ width: '100%', marginBottom: '15px' }} onClick={triggerValidation}>
                      {t('run_validation_btn')}
                    </button>

                    <div style={{ marginBottom: '8px' }}><strong>{t('active_phase_label')}:</strong> <span className="status-warn">{validationPhase}</span></div>
                    <div style={{ marginBottom: '8px' }}><strong>{t('component_boundaries_label')}:</strong> <span style={{ color: 'var(--primary)' }}>{validationComponent}</span></div>
                    <div style={{ marginBottom: '15px' }}><strong>{t('current_trace_label')}:</strong> <span style={{ color: 'var(--text-muted)' }}>{validationTrace}</span></div>

                    <div className="form-label">{t('live_trace_logs_label')}</div>
                    <div className="logs-box">
                      {validationLogs.map((log, idx) => <div key={idx}>{log}</div>)}
                    </div>
                  </div>

                  <div style={{ textAlign: 'center' }}>
                    <div className="score-circle">
                      <span style={{ fontSize: '0.75em', textAlign: 'center', color: 'var(--text-muted)' }}>{t('readiness_score_title')}</span>
                      <span className="score-num">{validationStatus.readiness_score || '0.0%'}</span>
                      <span style={{ fontSize: '0.8em', marginTop: '4px', color: 'var(--accent)' }}>
                        {validationStatus.phase === 'SUCCESS' ? 'Passed' : 'Ready'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* deep SCM reports table */}
              <div className="card">
                <h3>{t('admin_report_title')}</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>{t('col_symbol')}</th>
                        <th>{t('col_timeframe')}</th>
                        <th>{t('col_shadow_cycles')}</th>
                        <th>{t('col_wins_losses')}</th>
                        <th>{t('col_win_rate')}</th>
                        <th>{t('col_avg_confidence')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {adminReports.map((rep, idx) => (
                        <tr key={idx}>
                          <td>{rep.symbol}</td>
                          <td>{rep.timeframe}</td>
                          <td>{rep.total_cycles}</td>
                          <td>{rep.wins}/{rep.losses}</td>
                          <td>{rep.win_rate}%</td>
                          <td>{rep.avg_confidence}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* AUTHENTICATION VIEWS */}
          {hash === '#/login' && (
            <div id="shell-login">
              <form className="card" style={{ maxWidth: '450px', margin: '40px auto', borderTop: '5px solid var(--primary)' }} onSubmit={handleLogin}>
                <h2 style={{ marginTop: 0, color: 'var(--primary)', textAlign: 'center' }}>{t('login_title')}</h2>

                <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                  <button type="button" className="social-btn social-google" style={{ flex: 1 }} onClick={() => handleSocialLogin('Google')}>Google</button>
                  <button type="button" className="social-btn social-apple" style={{ flex: 1 }} onClick={() => handleSocialLogin('Apple')}>Apple</button>
                </div>

                <div className="form-group">
                  <label className="form-label">{t('email_label')}</label>
                  <input className="input-field" type="email" value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} required placeholder={t('email_placeholder')} />
                </div>
                <div className="form-group" style={{ marginBottom: '10px' }}>
                  <label className="form-label">{t('password_label')}</label>
                  <input className="input-field" type="password" value={loginPass} onChange={(e) => setLoginPass(e.target.value)} required placeholder={t('password_placeholder')} />
                </div>
                <div style={{ textAlign: 'end', marginBottom: '20px' }}>
                  <a href="#/forgot-password" style={{ color: 'var(--primary)', fontSize: '0.85em', decoration: 'none' }}>{t('forgot_link')}</a>
                </div>
                <button type="submit" className="btn" style={{ width: '100%' }}>{t('login_btn')}</button>

                <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.9em' }}>
                  <a href="#/register" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>{t('no_account')}</a>
                </div>
              </form>
            </div>
          )}

          {hash === '#/register' && (
            <div id="shell-register">
              <form className="card" style={{ maxWidth: '450px', margin: '40px auto', borderTop: '5px solid var(--primary)' }} onSubmit={handleRegister}>
                <h2 style={{ marginTop: 0, color: 'var(--primary)', textAlign: 'center' }}>{t('register_title')}</h2>

                <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                  <button type="button" className="social-btn social-google" style={{ flex: 1 }} onClick={() => handleSocialLogin('Google')}>Google</button>
                  <button type="button" className="social-btn social-apple" style={{ flex: 1 }} onClick={() => handleSocialLogin('Apple')}>Apple</button>
                </div>

                <div className="form-group">
                  <label className="form-label">{t('name_label')}</label>
                  <input className="input-field" type="text" value={registerName} onChange={(e) => setRegisterName(e.target.value)} required placeholder={t('name_placeholder')} />
                </div>
                <div className="form-group">
                  <label className="form-label">{t('email_label')}</label>
                  <input className="input-field" type="email" value={registerEmail} onChange={(e) => setRegisterEmail(e.target.value)} required placeholder={t('email_placeholder')} />
                </div>
                <div className="form-group" style={{ marginBottom: '25px' }}>
                  <label className="form-label">{t('password_label')}</label>
                  <input className="input-field" type="password" value={registerPass} onChange={(e) => setRegisterPass(e.target.value)} required placeholder={t('password_placeholder')} />
                </div>
                <button type="submit" className="btn" style={{ width: '100%' }}>{t('register_btn')}</button>

                <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.9em' }}>
                  <a href="#/login" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>{t('has_account')}</a>
                </div>
              </form>
            </div>
          )}

          {hash === '#/forgot-password' && (
            <div id="shell-forgot">
              <form className="card" style={{ maxWidth: '450px', margin: '40px auto', borderTop: '5px solid var(--primary)' }} onSubmit={handleForgot}>
                <h2 style={{ marginTop: 0, color: 'var(--primary)', textAlign: 'center' }}>{t('forgot_title')}</h2>
                <div className="form-group" style={{ marginBottom: '25px' }}>
                  <label className="form-label">{t('email_label')}</label>
                  <input className="input-field" type="email" value={forgotEmail} onChange={(e) => setForgotEmail(e.target.value)} required placeholder={t('email_placeholder')} />
                </div>
                <button type="submit" className="btn" style={{ width: '100%' }}>{t('forgot_btn')}</button>

                <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.9em' }}>
                  <a href="#/login" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>{t('has_account')}</a>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>

      {/* Floating Support Chatbot */}
      <div className="chatbot-widget" id="chat-widget">
        <div className="chatbot-header" onClick={toggleChatbot}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="ai-pulse"></div>
            <span>{t('assistant_title')}</span>
          </div>
          <span>▲ / ▼</span>
        </div>
        {chatOpen && (
          <div className="chatbot-body" id="chat-body" style={{ display: 'block' }}>
            <div className="chatbot-messages">
              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`chat-bubble ${msg.sender === 'bot' ? 'bot' : 'user'}`}>
                  {idx === 0 && msg.sender === 'bot' ? t('assistant_greet') : msg.text}
                </div>
              ))}
              <div ref={chatMessagesEndRef} />
            </div>
            <div className="chatbot-input-container">
              <input
                className="chatbot-input"
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder={t('assistant_placeholder') || "سوال خود را مطرح کنید..."}
                onKeyDown={(e) => e.key === 'Enter' && sendChatMessage()}
              />
              <button className="chatbot-send" onClick={sendChatMessage}>{t('assistant_send') || 'Send'}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <I18nProvider>
      <MainApp />
    </I18nProvider>
  );
}

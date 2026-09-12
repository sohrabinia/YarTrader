import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api.js';

export default function OperatorView({ t, lang = 'fa' }) {
  const [operatorStatus, setOperatorStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [statusError, setStatusError] = useState(null);

  const [taskDescription, setTaskDescription] = useState('Return the current Operator health status.');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitSuccess, setSubmitErrorSuccess] = useState(null);

  const [tasks, setTasks] = useState([]);
  const [loadingTasks, setLoadingTasks] = useState(false);

  const fetchOperatorStatus = async () => {
    setLoadingStatus(true);
    setStatusError(null);
    try {
      const res = await apiService.get('/api/admin/operator/status');
      setOperatorStatus(res);
    } catch (err) {
      console.error("Failed to fetch Operator status:", err);
      setStatusError(err.message || 'Unable to connect to YarOperator runtime');
      setOperatorStatus({
        connected: false,
        status: 'UNAVAILABLE',
        details: err.message || 'YarTrader.Operator external runtime service is not reachable.'
      });
    } finally {
      setLoadingStatus(false);
    }
  };

  const fetchTasks = async () => {
    setLoadingTasks(true);
    try {
      const res = await apiService.get('/api/admin/operator/tasks');
      if (res && res.tasks) {
        setTasks(res.tasks);
      }
    } catch (err) {
      console.warn("Could not fetch task history:", err);
    } finally {
      setLoadingTasks(false);
    }
  };

  useEffect(() => {
    fetchOperatorStatus();
    fetchTasks();
  }, []);

  const handleTaskSubmit = async (e) => {
    e.preventDefault();
    if (!taskDescription.trim()) return;

    setSubmitting(true);
    setSubmitError(null);
    setSubmitErrorSuccess(null);

    try {
      const res = await apiService.post('/api/admin/operator/tasks', {
        task_description: taskDescription,
        workspace_id: 'yartrader'
      });

      if (res && res.success) {
        setSubmitErrorSuccess(`Task successfully submitted (Task ID: ${res.task_id})`);
        fetchTasks();
        fetchOperatorStatus();
      } else {
        setSubmitError(res.error || res.details || 'Task execution failed.');
      }
    } catch (err) {
      console.error("Task submission error:", err);
      setSubmitError(err.message || 'Failed to submit task to YarOperator.');
    } finally {
      setSubmitting(false);
    }
  };

  const isConnected = operatorStatus && (operatorStatus.connected || operatorStatus.status === 'ONLINE');

  return (
    <div id="shell-operator" className="space-y-6">
      {/* HEADER CARD */}
      <div className="card" style={{ borderLeft: '4px solid var(--accent)' }}>
        <div className="flex flex-wrap justify-between items-center gap-4">
          <div>
            <h2 className="text-xl font-bold text-amber-400 mb-1 flex items-center gap-2">
              <span>🤖</span> {lang === 'fa' ? 'رابط اپراتور خودمختار YarOperator' : 'YarOperator Autonomous Interface'}
            </h2>
            <p className="text-sm text-[var(--text-dark)]">
              {lang === 'fa'
                ? 'ارسال، مدیریت و پایش مأموریت‌های اجرایی به موتور خودمختار YarOperator'
                : 'Direct, secure task delegation, monitoring and policy verification to YarOperator runtime.'}
            </p>
          </div>
          <button
            onClick={() => { fetchOperatorStatus(); fetchTasks(); }}
            className="btn btn-secondary text-xs px-3 py-1.5 flex items-center gap-1"
            disabled={loadingStatus}
          >
            <span>🔄</span> {loadingStatus ? (lang === 'fa' ? 'در حال پایش...' : 'Checking...') : (lang === 'fa' ? 'بروزرسانی وضعیت' : 'Refresh Status')}
          </button>
        </div>
      </div>

      {/* STATUS & CONNECTION CARD */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-5 space-y-2">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {lang === 'fa' ? 'وضعیت اتصال سرویس' : 'Connection Status'}
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <span className={`text-lg font-bold ${isConnected ? 'text-emerald-400' : 'text-red-400'}`}>
              {loadingStatus
                ? (lang === 'fa' ? 'در حال بررسی...' : 'Checking...')
                : isConnected
                ? (lang === 'fa' ? 'متصل و آماده (Connected / Ready)' : 'Connected & Ready')
                : (lang === 'fa' ? 'غیرقابل دسترس (Unavailable)' : 'Unavailable')}
            </span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed mt-2">
            {operatorStatus?.details || (lang === 'fa' ? 'درحال برقراری ارتباط با YarOperator...' : 'Connecting to YarOperator...')}
          </p>
        </div>

        <div className="card p-5 space-y-2">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {lang === 'fa' ? 'محیط و معماری سیستم' : 'Runtime Environment'}
          </div>
          <div className="text-base font-bold text-slate-200">
            {operatorStatus?.operator_runtime || 'YarTrader.Operator'}
          </div>
          <div className="text-xs text-slate-400 space-y-1">
            <div><strong>OS:</strong> {operatorStatus?.os_environment || 'Linux/Windows'}</div>
            <div><strong>Host:</strong> {operatorStatus?.host || '127.0.0.1'}:{operatorStatus?.port || 8890}</div>
          </div>
        </div>

        <div className="card p-5 space-y-2">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {lang === 'fa' ? 'آخرین استعلام سلامت' : 'Last Health Sync'}
          </div>
          <div className="text-sm font-mono text-amber-300">
            {operatorStatus?.timestamp
              ? new Date(operatorStatus.timestamp).toLocaleTimeString()
              : (lang === 'fa' ? 'نامشخص' : 'N/A')}
          </div>
          <div className="text-xs text-slate-400">
            {lang === 'fa' ? 'احرازهویت سرور-به-سرور: فعال (X-Operator-Server-Secret)' : 'Server-to-Server Auth: Active'}
          </div>
        </div>
      </div>

      {/* TASK SUBMISSION FORM */}
      <div className="card p-6 space-y-4">
        <h3 className="text-lg font-bold text-amber-400 flex items-center gap-2">
          <span>📝</span> {lang === 'fa' ? 'ارسال مأموریت جدید به YarOperator' : 'Submit Task to YarOperator'}
        </h3>
        <p className="text-xs text-slate-400">
          {lang === 'fa'
            ? 'دستور خود را وارد کنید. مأموریت به‌صورت امن از طریق هدرهای تاییدشده سرور به YarOperator منتقل و اجرا می‌گردد.'
            : 'Enter task description. Task will be securely dispatched to YarOperator via verified server identity.'}
        </p>

        <form onSubmit={handleTaskSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-2">
              {lang === 'fa' ? 'شرح مأموریت (Task Description)' : 'Task Description'}
            </label>
            <textarea
              rows={3}
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              placeholder="Return the current Operator health status."
              className="w-full p-3 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-amber-500 font-mono"
              required
            />
          </div>

          {submitError && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold">
              ⚠️ {submitError}
            </div>
          )}

          {submitSuccess && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
              ✅ {submitSuccess}
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting || !taskDescription.trim()}
              className="btn btn-primary px-6 py-2.5 text-sm font-bold flex items-center gap-2"
              style={{ backgroundColor: 'var(--accent)', color: '#000' }}
            >
              <span>🚀</span>
              {submitting
                ? (lang === 'fa' ? 'در حال ارسال و اجرا...' : 'Executing Task...')
                : (lang === 'fa' ? 'ارسال مأموریت واقعی (Submit Real Task)' : 'Submit Real Task')}
            </button>
          </div>
        </form>
      </div>

      {/* RECENT TASKS & EXECUTION RESULTS */}
      <div className="card p-6 space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <span>📋</span> {lang === 'fa' ? 'تاریخچه مأموریت‌ها و نتایج اجرای زنده' : 'Task History & Execution Results'}
          </h3>
          <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-mono">
            {tasks.length} {lang === 'fa' ? 'مأموریت ثبت شده' : 'Tasks Recorded'}
          </span>
        </div>

        {loadingTasks ? (
          <div className="text-center py-8 text-xs text-slate-400">
            {lang === 'fa' ? 'در حال دریافت اطلاعات مأموریت‌ها...' : 'Loading task history...'}
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
            {lang === 'fa' ? 'هیچ مأموریتی ثبت نشده است. از فرم بالا مأموریت جدیدی ارسال کنید.' : 'No tasks submitted yet. Enter a task above to execute.'}
          </div>
        ) : (
          <div className="space-y-4">
            {tasks.map((task, idx) => (
              <div key={task.task_id || idx} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <div className="flex flex-wrap justify-between items-center gap-2 border-b border-slate-800/80 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-amber-400 font-mono">Task ID: {task.task_id}</span>
                    <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full uppercase ${
                      task.status === 'COMPLETED' || task.status === 'SAFE' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                      task.status === 'FAILED' || task.status === 'BLOCKED' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                      'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    }`}>
                      {task.status || 'CREATED'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono">
                    {task.submitted_at ? new Date(task.submitted_at).toLocaleString() : ''}
                  </div>
                </div>

                <div className="text-xs text-slate-200">
                  <strong className="text-slate-400 block mb-1">{lang === 'fa' ? 'دستور مأموریت:' : 'Command:'}</strong>
                  <code className="block p-2 rounded bg-slate-950 text-amber-300 font-mono text-[12px]">{task.task_description}</code>
                </div>

                {task.result && (
                  <div className="text-xs text-slate-300">
                    <strong className="text-slate-400 block mb-1">{lang === 'fa' ? 'نتیجه و خروجی اجرای YarOperator:' : 'Operator Result Output:'}</strong>
                    <pre className="p-3 rounded bg-slate-950/80 text-emerald-300 font-mono text-[11px] overflow-x-auto border border-slate-800/60 leading-relaxed">
                      {typeof task.result === 'object' ? JSON.stringify(task.result, null, 2) : String(task.result)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

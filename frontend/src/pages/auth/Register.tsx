import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { User, Mail, KeyRound, Phone, AlertCircle, ArrowRight } from 'lucide-react';
import { DIRSLogo } from '../../components/design-system';

export const Register: React.FC = () => {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [role, setRole] = useState('CITIZEN');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register({ full_name: fullName, email, password, phone, role });
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian-950 flex flex-col justify-center items-center px-4 py-12 bg-grid-pattern text-slate-100 font-sans selection:bg-amber-ops selection:text-obsidian-950">
      <div className="w-full max-w-md bg-obsidian-850 border border-obsidian-700/80 rounded-xl p-8 shadow-2xl space-y-6">
        <div className="flex flex-col items-center text-center">
          <DIRSLogo size={64} className="justify-center mb-3" />
          <h1 className="text-xl font-mono font-bold text-slate-100 tracking-tight">
            REGISTER DIRS RESPONDER
          </h1>
          <p className="text-xs text-slate-400 font-sans mt-0.5">
            Join the Disaster Intelligence & Emergency Response Network
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-950/60 border border-red-800/80 rounded-lg flex items-center gap-2 text-xs text-red-300 font-mono">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-3.5 font-mono text-xs">
          <div>
            <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
              Full Official Name
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Dr. Samantha Chen"
                className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops focus:ring-1 focus:ring-amber-ops transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="responder@dirs.org"
                className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops focus:ring-1 focus:ring-amber-ops transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
              Contact Phone (Emergency Dispatch)
            </label>
            <div className="relative">
              <Phone className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 98400 12345"
                className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops focus:ring-1 focus:ring-amber-ops transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
              Operational Subsystem Role
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-amber-ops transition"
            >
              <option value="CITIZEN">Citizen / General Public</option>
              <option value="VOLUNTEER">Field Volunteer Responder</option>
              <option value="NGO">NGO Relief Agency</option>
              <option value="GOVT">Government Command Officer</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
              Security Password
            </label>
            <div className="relative">
              <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops focus:ring-1 focus:ring-amber-ops transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold py-2.5 rounded-lg text-xs font-mono transition mt-3 flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
          >
            {loading ? 'Creating Credentials...' : 'REGISTER & CREATE ACCESS'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <p className="text-center text-xs text-slate-500 font-sans">
          Already registered?{' '}
          <Link to="/login" className="text-amber-ops hover:underline font-mono">
            Sign In to Command
          </Link>
        </p>
      </div>
    </div>
  );
};

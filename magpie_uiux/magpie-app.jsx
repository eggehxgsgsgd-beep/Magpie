// Magpie App — Shell, Welcome, Dialogs, Keyboard handling
const { useState, useEffect, useCallback, useRef, useContext } = React;

/* ── Welcome Screen ── */
function WelcomeScreen({ onOpenSettings, onOpenFolder }) {
  const t = useContext(ThemeCtx);
  const [hov, setHov] = useState(null);
  return (
    <div style={{flex:1,display:'flex',alignItems:'center',justifyContent:'center',background:t.bg}}>
      <div style={{textAlign:'center',maxWidth:500,padding:40}}>
        <MI.Logo size={56}/>
        <h1 style={{fontSize:22,fontWeight:700,color:t.text,margin:'20px 0 8px',letterSpacing:'-0.01em'}}>
          欢迎使用 Magpie
        </h1>
        <p style={{fontSize:14,color:t.textSec,lineHeight:1.7,marginBottom:36}}>
          请先在 <strong style={{color:t.text}}>设置 → 类别</strong> 中定义你的分类按键，<br/>
          然后点击 <strong style={{color:t.text}}>打开图片文件夹</strong> 选择待分类的图片目录。
        </p>
        <div style={{display:'flex',gap:12,justifyContent:'center'}}>
          <button onClick={onOpenSettings}
            onMouseEnter={()=>setHov('s')} onMouseLeave={()=>setHov(null)}
            style={{
              display:'inline-flex',alignItems:'center',gap:8,
              padding:'11px 24px',borderRadius:8,border:`1px solid ${t.border}`,
              background:hov==='s'?t.surfaceHover:t.surface,color:t.text,
              fontSize:14,fontWeight:500,cursor:'pointer',transition:'all .15s',
            }}>
            <MI.Tune size={16}/> 打开设置
          </button>
          <button onClick={onOpenFolder}
            onMouseEnter={()=>setHov('f')} onMouseLeave={()=>setHov(null)}
            style={{
              display:'inline-flex',alignItems:'center',gap:8,
              padding:'11px 24px',borderRadius:8,border:'none',
              background:hov==='f'?t.accentHover:t.accent,color:'#fff',
              fontSize:14,fontWeight:500,cursor:'pointer',transition:'all .15s',
            }}>
            <MI.Folder size={16}/> 打开图片文件夹
          </button>
        </div>
        <div style={{marginTop:40,display:'flex',justifyContent:'center',gap:20,
          fontSize:11,color:t.textTer}}>
          <span>Ctrl+O 打开文件夹</span>
          <span>Ctrl+, 打开设置</span>
          <span>← → 浏览图片</span>
        </div>
      </div>
    </div>
  );
}

/* ── Conflict Dialog ── */
function ConflictDialog({ conflict, onResolve }) {
  const t = useContext(ThemeCtx);
  const [remember, setRemember] = useState(false);
  if (!conflict) return null;
  const { imgId, cat } = conflict;
  const img = IMAGES[imgId];
  const actions = [
    {id:'skip',label:'跳过',bg:'transparent',clr:t.textSec,bdr:`1px solid ${t.border}`},
    {id:'override',label:'覆盖',bg:t.danger,clr:'#fff',bdr:'none'},
    {id:'rename',label:'重命名',bg:t.surfaceHover,clr:t.text,bdr:`1px solid ${t.border}`},
    {id:'cancel',label:'取消',bg:'transparent',clr:t.textSec,bdr:`1px solid ${t.border}`},
  ];
  return (
    <div style={{position:'fixed',inset:0,zIndex:200,display:'flex',alignItems:'center',
      justifyContent:'center',background:t.backdrop,animation:'fadeIn .12s ease-out'}}>
      <div style={{width:420,background:t.dialogBg,borderRadius:12,
        boxShadow:'0 20px 60px rgba(0,0,0,0.4)',padding:24,
        animation:'scaleIn .18s ease-out'}}>
        <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:14}}>
          <MI.Alert size={20} style={{color:t.warning}}/>
          <span style={{fontSize:15,fontWeight:600,color:t.text}}>文件冲突</span>
        </div>
        <p style={{fontSize:13,color:t.textSec,lineHeight:1.6,marginBottom:8}}>目标位置已存在同名文件：</p>
        <div style={{padding:'8px 12px',background:t.inputBg,borderRadius:6,
          fontFamily:'monospace',fontSize:12,color:t.text,marginBottom:16}}>
          {cat.folder}/{img?.name}
        </div>
        <label style={{display:'flex',alignItems:'center',gap:8,marginBottom:20,cursor:'pointer'}}>
          <input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)}
            style={{accentColor:t.accent,width:14,height:14}}/>
          <span style={{fontSize:12,color:t.textSec}}>对本次会话记住此选择</span>
        </label>
        <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
          {actions.map(a => (
            <button key={a.id} onClick={()=>onResolve(a.id)} style={{
              padding:'7px 16px',borderRadius:6,fontSize:13,fontWeight:500,cursor:'pointer',
              background:a.bg,color:a.clr,border:a.bdr,transition:'all .15s',
            }}>{a.label}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Jump Dialog ── */
function JumpDialog({ open, onClose, onJump, total }) {
  const t = useContext(ThemeCtx);
  const [val, setVal] = useState('');
  const ref = useRef(null);
  useEffect(() => { if(open) { setVal(''); setTimeout(()=>ref.current?.focus(),100); } }, [open]);
  if (!open) return null;
  const submit = (e) => {
    e.preventDefault();
    const n = parseInt(val);
    if(n>=1 && n<=total) { onJump(n-1); onClose(); }
  };
  return (
    <div style={{position:'fixed',inset:0,zIndex:200,display:'flex',alignItems:'center',
      justifyContent:'center',background:t.backdrop,animation:'fadeIn .12s ease-out'}}
      onClick={e=>{if(e.target===e.currentTarget) onClose();}}>
      <form onSubmit={submit} style={{width:320,background:t.dialogBg,borderRadius:12,
        boxShadow:'0 20px 60px rgba(0,0,0,0.4)',padding:20,animation:'scaleIn .18s ease-out'}}
        onClick={e=>e.stopPropagation()}>
        <div style={{fontSize:14,fontWeight:600,color:t.text,marginBottom:12}}>跳转到图片</div>
        <div style={{display:'flex',gap:8}}>
          <input ref={ref} type="number" min={1} max={total} value={val}
            onChange={e=>setVal(e.target.value)}
            placeholder={`输入 1 — ${total}`}
            style={{flex:1,height:38,padding:'0 12px',background:t.inputBg,
              border:`1px solid ${t.inputBorder}`,borderRadius:6,
              fontSize:14,color:t.text,outline:'none'}}/>
          <button type="submit" style={{padding:'0 18px',height:38,borderRadius:6,border:'none',
            background:t.accent,color:'#fff',fontSize:13,fontWeight:500,cursor:'pointer'}}>
            跳转
          </button>
        </div>
      </form>
    </div>
  );
}

/* ── Toast ── */
function MagpieToast({ toast }) {
  if (!toast) return null;
  const t = useContext(ThemeCtx);
  return (
    <div style={{position:'fixed',bottom:48,left:'50%',transform:'translateX(-50%)',
      zIndex:300,animation:'toastIn .2s ease-out',pointerEvents:'none'}}>
      <div style={{display:'flex',alignItems:'center',gap:8,
        padding:'8px 22px',borderRadius:8,
        background:t.toastBg,color:t.toastText,
        fontSize:13,fontWeight:500,
        boxShadow:'0 4px 20px rgba(0,0,0,0.35)',
        border:`1px solid ${toast.color}40`}}>
        <div style={{width:8,height:8,borderRadius:'50%',background:toast.color,flexShrink:0}}/>
        {toast.msg}
      </div>
    </div>
  );
}

/* ── Main App ── */
function MagpieApp({ tweaks }) {
  const theme = THEMES[tweaks.theme] || THEMES.dark;
  const s = useMagpie();

  // Keyboard handler
  useEffect(() => {
    if (s.settings || s.conflict || s.jump) return;
    const handler = (e) => {
      if (['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return;
      const ctrl = e.ctrlKey || e.metaKey;
      // Global
      if (ctrl && e.key===',') { e.preventDefault(); s.setSettings(true); return; }
      if (ctrl && e.key.toLowerCase()==='o') { e.preventDefault(); s.openFolder(); return; }
      if (s.screen !== 'classify') return;
      switch(e.key) {
        case 'ArrowLeft': e.preventDefault(); s.prev(); break;
        case 'ArrowRight': e.preventDefault(); s.next(); break;
        case ' ': e.preventDefault(); s.setPlaying(p=>!p); break;
        case 'b': case 'B': if(!ctrl) s.setBBox(b=>!b); break;
        default:
          if (ctrl && (e.key==='z'||e.key==='Z')) { e.preventDefault(); e.shiftKey?s.redo():s.undo(); }
          else if (ctrl && (e.key==='y'||e.key==='Y')) { e.preventDefault(); s.redo(); }
          else if (ctrl && (e.key==='g'||e.key==='G')) { e.preventDefault(); s.setJump(true); }
          else if (!ctrl && !e.altKey) {
            const cat = s.cats.find(c => c.key === e.key);
            if (cat) { e.preventDefault(); s.classify(cat.folder); }
          }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [s.screen, s.settings, s.conflict, s.jump, s.cats,
      s.prev, s.next, s.setPlaying, s.setBBox, s.undo, s.redo,
      s.setJump, s.openFolder, s.classify, s.setSettings]);

  return (
    <ThemeCtx.Provider value={theme}>
      <div style={{
        width:'100vw',height:'100vh',display:'flex',flexDirection:'column',
        background:theme.bg,color:theme.text,overflow:'hidden',
        fontFamily:'-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Segoe UI",system-ui,sans-serif',
        fontSize:14,transition:'background .25s, color .25s',
      }}>
        <MagpieToolbar s={s}/>
        {s.screen==='welcome' ? (
          <WelcomeScreen onOpenSettings={()=>s.setSettings(true)} onOpenFolder={s.openFolder}/>
        ) : (
          <div style={{flex:1,display:'flex',
            flexDirection:tweaks.layout==='bottom'?'column':'row',
            overflow:'hidden'}}>
            <ImageViewer s={s} tweaks={tweaks}/>
            <CategoryPanel s={s} tweaks={tweaks}/>
          </div>
        )}
        <StatusBar s={s}/>
        <SettingsDialog open={s.settings} onClose={()=>s.setSettings(false)}
          cats={s.cats} setCats={s.setCats}/>
        <ConflictDialog conflict={s.conflict} onResolve={s.resolveConflict}/>
        <JumpDialog open={s.jump} onClose={()=>s.setJump(false)} onJump={s.goTo} total={s.total}/>
        <MagpieToast toast={s.toast}/>
      </div>
    </ThemeCtx.Provider>
  );
}

Object.assign(window, { MagpieApp });

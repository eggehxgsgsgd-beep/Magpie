// Magpie Settings Dialog — 5 tabs
const { useState: _su, useEffect: _se, useContext: _sc, useRef: _sr } = React;

/* ── Shared form controls ── */
function SField({ label, desc, children }) {
  const t = _sc(ThemeCtx);
  return (
    <div style={{marginBottom:16}}>
      <label style={{fontSize:13,color:t.text,fontWeight:500,marginBottom:4,display:'block'}}>{label}</label>
      {children}
      {desc && <div style={{fontSize:11,color:t.textTer,marginTop:4}}>{desc}</div>}
    </div>
  );
}

function SToggle({ label, value, onChange }) {
  const t = _sc(ThemeCtx);
  return (
    <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'8px 0'}}>
      <span style={{fontSize:13,color:t.text}}>{label}</span>
      <div onClick={()=>onChange(!value)} style={{
        width:36,height:20,borderRadius:10,padding:2,cursor:'pointer',
        background:value?t.accent:t.surfaceActive,transition:'background .2s',
      }}>
        <div style={{width:16,height:16,borderRadius:8,background:'#fff',
          transform:value?'translateX(16px)':'translateX(0)',transition:'transform .2s'}}/>
      </div>
    </div>
  );
}

function SSelect({ label, value, onChange, options }) {
  const t = _sc(ThemeCtx);
  return (
    <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'8px 0'}}>
      <span style={{fontSize:13,color:t.text}}>{label}</span>
      <select value={value} onChange={e=>onChange(e.target.value)} style={{
        height:30,padding:'0 8px',background:t.inputBg,
        border:`1px solid ${t.inputBorder}`,borderRadius:4,
        fontSize:13,color:t.text,outline:'none',minWidth:120,
      }}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

function SSlider({ label, value, onChange, min, max, step, unit }) {
  const t = _sc(ThemeCtx);
  return (
    <div style={{padding:'8px 0'}}>
      <div style={{display:'flex',justifyContent:'space-between',marginBottom:4}}>
        <span style={{fontSize:13,color:t.text}}>{label}</span>
        <span style={{fontSize:12,color:t.textSec,fontFamily:'monospace'}}>{value}{unit}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e=>onChange(Number(e.target.value))}
        style={{width:'100%',accentColor:t.accent}}/>
    </div>
  );
}

function SBtn({ children, primary, danger, onClick, style: sx }) {
  const t = _sc(ThemeCtx);
  const [hov, setHov] = _su(false);
  const bg = primary ? t.accent : danger ? t.danger : hov ? t.surfaceHover : 'transparent';
  const clr = (primary||danger) ? '#fff' : t.text;
  const bdr = (primary||danger) ? 'none' : `1px solid ${t.border}`;
  return (
    <button onClick={onClick}
      onMouseEnter={()=>setHov(true)} onMouseLeave={()=>setHov(false)}
      style={{padding:'7px 18px',borderRadius:6,fontSize:13,fontWeight:500,cursor:'pointer',
        background:bg,color:clr,border:bdr,transition:'all .15s',...sx}}>
      {children}
    </button>
  );
}

/* ── Tab: Categories ── */
function CategoriesTab({ localCats, setLocalCats }) {
  const t = _sc(ThemeCtx);
  const [capKey, setCapKey] = _su(null);

  _se(() => {
    if (capKey === null) return;
    const handler = (e) => {
      e.preventDefault();
      e.stopPropagation();
      const k = e.key;
      if (k === 'Escape') { setCapKey(null); return; }
      const reserved = ['f','b','0',' ','arrowleft','arrowright','arrowup','arrowdown'];
      if (reserved.includes(k.toLowerCase())) return;
      if (k.length === 1 && /[a-zA-Z0-9\-=\[\];',./\\`]/.test(k)) {
        const existing = localCats.findIndex((c,i) => i!==capKey && c.key===k);
        if (existing >= 0) return;
        const next = [...localCats];
        next[capKey] = {...next[capKey], key:k};
        setLocalCats(next);
      }
      setCapKey(null);
    };
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
  }, [capKey, localCats, setLocalCats]);

  const update = (i, field, val) => {
    const next = [...localCats];
    next[i] = {...next[i], [field]:val};
    setLocalCats(next);
  };
  const remove = (i) => setLocalCats(localCats.filter((_,j)=>j!==i));
  const add = () => {
    const clr = CAT_COLORS[localCats.length % CAT_COLORS.length];
    setLocalCats([...localCats, {key:'',folder:'',display:'',color:clr}]);
  };

  const inputSt = {height:30,padding:'0 8px',background:t.inputBg,
    border:`1px solid ${t.inputBorder}`,borderRadius:4,fontSize:13,color:t.text,
    outline:'none',width:'100%'};

  return (
    <div>
      <div style={{fontSize:14,fontWeight:600,color:t.text,marginBottom:4}}>类别配置</div>
      <div style={{fontSize:12,color:t.textSec,marginBottom:16,lineHeight:1.5}}>
        为每个分类定义快捷键、文件夹名和显示名称。点击快捷键单元格可捕获新按键。
      </div>
      {/* Header */}
      <div style={{display:'grid',gridTemplateColumns:'28px 48px 1fr 1fr 32px 32px',
        gap:8,padding:'6px 0',borderBottom:`1px solid ${t.border}`,
        fontSize:11,color:t.textTer,fontWeight:600}}>
        <span></span><span>键</span><span>文件夹名</span><span>显示名称</span><span>色</span><span></span>
      </div>
      {/* Rows */}
      {localCats.map((cat,i) => (
        <div key={i} style={{display:'grid',gridTemplateColumns:'28px 48px 1fr 1fr 32px 32px',
          gap:8,padding:'8px 0',alignItems:'center',
          borderBottom:`1px solid ${t.border}10`}}>
          <MI.Grip size={14} style={{color:t.textTer,cursor:'grab',justifySelf:'center'}}/>
          <div onClick={()=>setCapKey(i)} style={{
            height:30,display:'flex',alignItems:'center',justifyContent:'center',
            background:capKey===i?t.accentBg:t.inputBg,
            border:`1px solid ${capKey===i?t.accent:t.inputBorder}`,
            borderRadius:4,fontSize:14,fontWeight:700,fontFamily:'monospace',
            color:capKey===i?t.accent:t.text,cursor:'pointer',
            transition:'all .15s',
          }}>
            {capKey===i ? <span style={{fontSize:10,fontWeight:400}}>…</span> : (cat.key||'—')}
          </div>
          <input value={cat.folder} onChange={e=>update(i,'folder',e.target.value)}
            placeholder="folder_name" style={inputSt}/>
          <input value={cat.display} onChange={e=>update(i,'display',e.target.value)}
            placeholder="显示名称" style={inputSt}/>
          <div style={{width:30,height:30,borderRadius:4,background:cat.color,
            border:`2px solid ${t.border}`,cursor:'pointer'}}/>
          <button onClick={()=>remove(i)} style={{
            width:30,height:30,display:'flex',alignItems:'center',justifyContent:'center',
            background:'transparent',border:'none',borderRadius:4,
            color:t.textTer,cursor:'pointer'}}>
            <MI.Trash size={14}/>
          </button>
        </div>
      ))}
      <button onClick={add} style={{
        display:'flex',alignItems:'center',gap:6,marginTop:12,
        padding:'7px 14px',background:'transparent',border:`1px dashed ${t.border}`,
        borderRadius:6,color:t.textSec,fontSize:13,cursor:'pointer',width:'100%',
        justifyContent:'center',
      }}>
        <MI.Plus size={14}/> 添加类别
      </button>
    </div>
  );
}

/* ── Tab: Folders ── */
function FoldersTab() {
  const t = _sc(ThemeCtx);
  const fields = [
    {label:'默认图片来源目录',val:'/Users/demo/datasets/',desc:'打开图片文件夹对话框的起始路径'},
    {label:'默认输出目录',val:'/Users/demo/output/',desc:'分类结果的根目录，每个类别创建同名子文件夹'},
    {label:'默认标签目录 (可选)',val:'/Users/demo/labels/',desc:'YOLO label 文件目录'},
    {label:'classes.txt 路径 (可选)',val:'',desc:'指定后覆盖 BBox 类别名显示'},
  ];
  return (
    <div>
      <div style={{fontSize:14,fontWeight:600,color:t.text,marginBottom:16}}>文件夹设置</div>
      {fields.map((f,i) => (
        <SField key={i} label={f.label} desc={f.desc}>
          <div style={{display:'flex',gap:8}}>
            <input value={f.val} readOnly style={{
              flex:1,height:32,padding:'0 10px',background:t.inputBg,
              border:`1px solid ${t.inputBorder}`,borderRadius:4,
              fontSize:12,color:t.text,fontFamily:'monospace',outline:'none'}}/>
            <SBtn>选择…</SBtn>
          </div>
        </SField>
      ))}
    </div>
  );
}

/* ── Tab: Display ── */
function DisplayTab() {
  const [interval, setInterval_] = _su(100);
  const [showBB, setShowBB] = _su(true);
  const [showMark, setShowMark] = _su(true);
  const [theme, setTheme] = _su('system');
  return (
    <div>
      <div style={{fontSize:14,fontWeight:600,color:_sc(ThemeCtx).text,marginBottom:16}}>显示设置</div>
      <SSlider label="自动播放间隔" value={interval} onChange={setInterval_} min={50} max={2000} step={50} unit="ms"/>
      <SToggle label="默认显示 BBox" value={showBB} onChange={setShowBB}/>
      <SToggle label="显示已分类标记" value={showMark} onChange={setShowMark}/>
      <SSelect label="主题" value={theme} onChange={setTheme} options={[
        {value:'system',label:'跟随系统'},{value:'light',label:'浅色'},{value:'dark',label:'深色'}
      ]}/>
    </div>
  );
}

/* ── Tab: Behavior ── */
function BehaviorTab() {
  const t = _sc(ThemeCtx);
  const [op, setOp] = _su('copy');
  const [undoToast, setUndoToast] = _su(false);
  const [endBehav, setEndBehav] = _su('stay');
  const [types, setTypes] = _su(['jpg','jpeg','png','bmp','webp','tiff']);
  const allTypes = ['jpg','jpeg','png','bmp','webp','tiff','gif','svg'];
  const toggleType = (tp) => setTypes(ts => ts.includes(tp) ? ts.filter(x=>x!==tp) : [...ts, tp]);
  return (
    <div>
      <div style={{fontSize:14,fontWeight:600,color:t.text,marginBottom:16}}>行为设置</div>
      <SSelect label="默认操作" value={op} onChange={setOp} options={[
        {value:'copy',label:'复制'},{value:'move',label:'移动'}
      ]}/>
      <SToggle label="撤销后弹提示框" value={undoToast} onChange={setUndoToast}/>
      <SSelect label="到达末尾时" value={endBehav} onChange={setEndBehav} options={[
        {value:'stay',label:'停留'},{value:'prompt',label:'提示'},{value:'loop',label:'循环'}
      ]}/>
      <div style={{padding:'8px 0'}}>
        <div style={{fontSize:13,color:t.text,marginBottom:8}}>支持的文件类型</div>
        <div style={{display:'flex',flexWrap:'wrap',gap:6}}>
          {allTypes.map(tp => (
            <label key={tp} style={{display:'flex',alignItems:'center',gap:4,cursor:'pointer',
              padding:'4px 10px',borderRadius:4,fontSize:12,
              background:types.includes(tp)?t.accentBg:'transparent',
              border:`1px solid ${types.includes(tp)?t.accent:t.border}`,
              color:types.includes(tp)?t.accent:t.textSec}}>
              <input type="checkbox" checked={types.includes(tp)} onChange={()=>toggleType(tp)}
                style={{display:'none'}}/>
              .{tp}
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Tab: Import / Export ── */
function ImportExportTab() {
  const t = _sc(ThemeCtx);
  return (
    <div>
      <div style={{fontSize:14,fontWeight:600,color:t.text,marginBottom:4}}>导入 / 导出</div>
      <div style={{fontSize:12,color:t.textSec,marginBottom:20,lineHeight:1.5}}>
        将类别配置与偏好导出为预设文件 (.magpie-preset.json)，方便分享给团队成员。
      </div>
      <div style={{display:'flex',flexDirection:'column',gap:10}}>
        <SBtn onClick={()=>{}} style={{justifyContent:'center',display:'flex',alignItems:'center',gap:6}}>
          <MI.Download size={15}/> 导出预设
        </SBtn>
        <SBtn onClick={()=>{}} style={{justifyContent:'center',display:'flex',alignItems:'center',gap:6}}>
          <MI.Upload size={15}/> 导入预设
        </SBtn>
        <div style={{borderTop:`1px solid ${t.border}`,margin:'8px 0'}}/>
        <SBtn danger onClick={()=>{}} style={{justifyContent:'center',display:'flex',alignItems:'center',gap:6}}>
          重置为默认
        </SBtn>
      </div>
    </div>
  );
}

/* ── Settings Dialog Shell ── */
function SettingsDialog({ open, onClose, cats, setCats }) {
  const t = _sc(ThemeCtx);
  const [tab, setTab] = _su(0);
  const [localCats, setLocalCats] = _su([]);

  _se(() => { if(open) setLocalCats(cats.map(c=>({...c}))); }, [open, cats]);

  if (!open) return null;

  const tabs = ['类别','文件夹','显示','行为','导入/导出'];
  const handleApply = () => { setCats(localCats); onClose(); };

  return (
    <div style={{position:'fixed',inset:0,zIndex:100,display:'flex',alignItems:'center',
      justifyContent:'center',background:t.backdrop,animation:'fadeIn .15s ease-out'}}
      onClick={e=>{if(e.target===e.currentTarget) onClose();}}>
      <div style={{width:700,height:520,display:'flex',background:t.dialogBg,
        borderRadius:12,boxShadow:'0 20px 60px rgba(0,0,0,0.4)',overflow:'hidden',
        animation:'scaleIn .2s ease-out'}}
        onClick={e=>e.stopPropagation()}>
        {/* Tabs */}
        <div style={{width:170,padding:'16px 0',borderRight:`1px solid ${t.border}`,
          display:'flex',flexDirection:'column',flexShrink:0}}>
          <div style={{padding:'4px 16px 16px',fontSize:15,fontWeight:600,color:t.text}}>设置</div>
          {tabs.map((tb,i) => (
            <div key={i} onClick={()=>setTab(i)} style={{
              padding:'9px 16px',margin:'1px 8px',borderRadius:6,cursor:'pointer',
              background:tab===i?t.accentBg:'transparent',
              color:tab===i?t.accent:t.textSec,
              fontSize:13,fontWeight:tab===i?600:400,transition:'all .15s',
            }}>{tb}</div>
          ))}
        </div>
        {/* Content */}
        <div style={{flex:1,display:'flex',flexDirection:'column',minWidth:0}}>
          <div style={{flex:1,overflow:'auto',padding:24}}>
            {tab===0 && <CategoriesTab localCats={localCats} setLocalCats={setLocalCats}/>}
            {tab===1 && <FoldersTab/>}
            {tab===2 && <DisplayTab/>}
            {tab===3 && <BehaviorTab/>}
            {tab===4 && <ImportExportTab/>}
          </div>
          <div style={{display:'flex',justifyContent:'flex-end',gap:8,padding:'12px 24px',
            borderTop:`1px solid ${t.border}`}}>
            <SBtn onClick={onClose}>取消</SBtn>
            <SBtn primary onClick={handleApply}>应用</SBtn>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SettingsDialog });

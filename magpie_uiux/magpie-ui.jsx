// Magpie UI — Toolbar, ImageViewer, CategoryPanel, StatusBar
const { useState: _us, useContext: _uc } = React;

/* ── Toolbar Button ── */
function ToolBtn({ icon, label, active, disabled, onClick, toggled }) {
  const t = _uc(ThemeCtx);
  const [hov, setHov] = _us(false);
  const bg = toggled ? t.accentBg : (hov && !disabled) ? t.surfaceHover : 'transparent';
  const clr = disabled ? t.textTer : toggled ? t.accent : t.textSec;
  return (
    <button onClick={disabled ? undefined : onClick}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      title={label}
      style={{
        display:'flex', alignItems:'center', justifyContent:'center',
        width:32, height:32, border:'none', borderRadius:6,
        background:bg, color:clr, cursor:disabled?'default':'pointer',
        opacity:disabled?.4:1, transition:'all .15s', flexShrink:0,
      }}>
      {icon}
    </button>
  );
}
function ToolSep() {
  const t = _uc(ThemeCtx);
  return <div style={{width:1,height:18,background:t.border,margin:'0 4px',flexShrink:0}}/>;
}

/* ── Toolbar ── */
function MagpieToolbar({ s }) {
  const t = _uc(ThemeCtx);
  const ok = s.screen==='classify';
  return (
    <div style={{
      display:'flex', alignItems:'center', gap:2, padding:'0 10px',
      height:44, background:t.toolbarBg, borderBottom:`1px solid ${t.toolbarBorder}`,
      flexShrink:0, userSelect:'none',
    }}>
      <div style={{display:'flex',alignItems:'center',gap:7,marginRight:6}}>
        <MI.Logo size={22}/> 
        <span style={{fontSize:13,fontWeight:600,color:t.text,letterSpacing:'.02em'}}>Magpie</span>
      </div>
      <ToolSep/>
      <ToolBtn icon={<MI.Folder/>} label="打开文件夹 (Ctrl+O)" onClick={s.openFolder}/>
      <ToolSep/>
      <ToolBtn icon={<MI.Left/>} label="上一张 (←)" onClick={s.prev} disabled={!ok||s.idx===0}/>
      <ToolBtn icon={<MI.Right/>} label="下一张 (→)" onClick={s.next} disabled={!ok||s.idx>=s.total-1}/>
      <ToolBtn icon={s.playing?<MI.Pause/>:<MI.Play/>} label="自动播放 (Space)"
        onClick={()=>s.setPlaying(!s.playing)} toggled={s.playing} disabled={!ok}/>
      <ToolBtn icon={<MI.Jump/>} label="跳转 (Ctrl+G)" onClick={()=>s.setJump(true)} disabled={!ok}/>
      <ToolSep/>
      <ToolBtn icon={<MI.Undo/>} label={`撤销 (Ctrl+Z) [${s.undos.length}]`} onClick={s.undo} disabled={!s.undos.length}/>
      <ToolBtn icon={<MI.Redo/>} label={`重做 (Ctrl+Y) [${s.redos.length}]`} onClick={s.redo} disabled={!s.redos.length}/>
      <ToolSep/>
      <ToolBtn
        icon={s.mode==='copy'?<MI.Copy/>:<MI.Move/>}
        label={s.mode==='copy'?'复制模式 (点击切换)':'移动模式 (点击切换)'}
        onClick={()=>s.setMode(m=>m==='copy'?'move':'copy')}
        toggled={s.mode==='move'} disabled={!ok}/>
      <ToolSep/>
      <ToolBtn icon={<MI.Fit/>} label="适应窗口 (F)" disabled={!ok}/>
      <ToolBtn icon={<MI.BBox/>} label="BBox 显示 (B)" onClick={()=>s.setBBox(!s.bbox)} toggled={s.bbox} disabled={!ok}/>
      <div style={{flex:1}}/>
      <ToolBtn icon={<MI.Tune/>} label="设置 (Ctrl+,)" onClick={()=>s.setSettings(true)}/>
    </div>
  );
}

/* ── Image Viewer ── */
function ImageViewer({ s, tweaks }) {
  const t = _uc(ThemeCtx);
  const img = s.img;
  if (!img) return null;

  const bboxes = s.bbox ? (BBOXES[s.idx]||[]) : [];
  const imgCls = s.cls[s.idx];
  const lastFolder = imgCls?.[imgCls.length-1];
  const cat = lastFolder && s.cats.find(c => c.folder===lastFolder);
  const aspect = img.w / img.h;
  const isLand = aspect >= 1;

  return (
    <div style={{
      flex:1, display:'flex', alignItems:'center', justifyContent:'center',
      background:t.viewerBg, position:'relative', overflow:'hidden', minWidth:0,
    }}>
      {/* Photo placeholder */}
      <div key={s.idx} style={{
        position:'relative',
        width: isLand ? '72%' : 'auto', height: isLand ? 'auto' : '78%',
        aspectRatio:`${img.w}/${img.h}`,
        maxWidth:'84%', maxHeight:'84%',
        borderRadius:2, overflow:'hidden',
        boxShadow:'0 4px 24px rgba(0,0,0,0.4)',
        animation:'imgIn .18s ease-out',
      }}>
        <div style={{position:'absolute',inset:0,
          background:`linear-gradient(135deg,${img.grad[0]},${img.grad[1]})`}}/>
        <div style={{position:'absolute',inset:0,
          background:'repeating-linear-gradient(45deg,transparent,transparent 14px,rgba(255,255,255,0.025) 14px,rgba(255,255,255,0.025) 28px)'}}/>
        <div style={{position:'absolute',inset:0,display:'flex',flexDirection:'column',
          alignItems:'center',justifyContent:'center',gap:8}}>
          <span style={{fontFamily:'monospace',fontSize:14,color:'rgba(255,255,255,0.45)',
            padding:'6px 18px',background:'rgba(0,0,0,0.3)',borderRadius:4,letterSpacing:'.04em'}}>
            [ {img.label} ]
          </span>
          <span style={{fontFamily:'monospace',fontSize:11,color:'rgba(255,255,255,0.25)'}}>
            {img.name} · {img.w}×{img.h}
          </span>
        </div>

        {/* BBox overlays */}
        {bboxes.map((box, i) => {
          const bc = s.cats[box.cls]?.color || '#78716C';
          const bl = s.cats[box.cls]?.display || `class ${box.cls}`;
          return (
            <div key={i} style={{
              position:'absolute',
              left:`${(box.cx-box.w/2)*100}%`, top:`${(box.cy-box.h/2)*100}%`,
              width:`${box.w*100}%`, height:`${box.h*100}%`,
              border:`2px solid ${bc}`, background:`${bc}15`, borderRadius:2,
            }}>
              <span style={{
                position:'absolute', top:-22, left:-2,
                background:bc, color:'#fff', padding:'2px 7px',
                fontSize:11, fontWeight:600, borderRadius:3,
                whiteSpace:'nowrap', lineHeight:'16px',
              }}>{bl} {box.cf.toFixed(2)}</span>
            </div>
          );
        })}
      </div>

      {/* Classification badge */}
      {imgCls && cat && (
        tweaks.badgeStyle==='tag' ? (
          <div style={{position:'absolute',top:12,left:12,
            background:cat.color, padding:'4px 14px', borderRadius:4}}>
            <span style={{fontSize:12,color:'#fff',fontWeight:600}}>{cat.display}</span>
          </div>
        ) : (
          <div style={{position:'absolute',top:12,left:12,display:'flex',alignItems:'center',gap:6,
            background:'rgba(0,0,0,0.7)',backdropFilter:'blur(8px)',
            padding:'5px 12px',borderRadius:6,border:`1px solid ${cat.color}40`}}>
            <div style={{width:8,height:8,borderRadius:'50%',background:cat.color}}/>
            <span style={{fontSize:12,color:'#fff',fontWeight:500}}>已分类: {cat.display}</span>
          </div>
        )
      )}

      {/* Image counter overlay */}
      <div style={{position:'absolute',bottom:12,right:12,display:'flex',alignItems:'center',gap:6,
        fontSize:11,color:'rgba(255,255,255,0.35)',fontFamily:'monospace'}}>
        适应窗口
      </div>

      {/* Auto-play indicator */}
      {s.playing && (
        <div style={{position:'absolute',top:12,right:12,display:'flex',alignItems:'center',gap:5,
          background:'rgba(0,0,0,0.6)',backdropFilter:'blur(8px)',padding:'4px 10px',borderRadius:6}}>
          <div style={{width:6,height:6,borderRadius:'50%',background:'#EF4444',
            animation:'pulse 1s infinite'}}/>
          <span style={{fontSize:11,color:'rgba(255,255,255,0.7)',fontWeight:500}}>自动播放中</span>
        </div>
      )}
    </div>
  );
}

/* ── Category Panel ── */
function CategoryPanel({ s, tweaks }) {
  const t = _uc(ThemeCtx);
  const isBottom = tweaks.layout==='bottom';

  if (isBottom) {
    return (
      <div style={{display:'flex',alignItems:'center',gap:6,padding:'0 12px',
        height:50,background:t.panelBg,borderTop:`1px solid ${t.border}`,
        flexShrink:0,overflowX:'auto'}}>
        {s.cats.map(cat => {
          const fl = s.flash===cat.folder;
          const cnt = s.counts[cat.folder]||0;
          return (
            <div key={cat.key} onClick={()=>s.classify(cat.folder)} style={{
              display:'flex',alignItems:'center',gap:6,padding:'6px 14px',
              borderRadius:6,background:fl?`${cat.color}20`:'transparent',
              border:`1px solid ${fl?cat.color:t.border}`,
              transition:'all .2s',whiteSpace:'nowrap',cursor:'pointer',
            }}>
              <div style={{width:8,height:8,borderRadius:'50%',background:cat.color,flexShrink:0}}/>
              <span style={{display:'inline-flex',alignItems:'center',justifyContent:'center',
                width:20,height:20,borderRadius:4,background:t.surfaceHover,
                fontSize:11,fontWeight:600,color:t.textSec,fontFamily:'monospace'}}>{cat.key}</span>
              <span style={{fontSize:13,color:t.text,fontWeight:500}}>{cat.display}</span>
              {cnt>0 && <span style={{fontSize:11,color:t.textTer,fontFamily:'monospace'}}>{cnt}</span>}
            </div>
          );
        })}
        <div style={{marginLeft:'auto',fontSize:12,color:t.textTer,whiteSpace:'nowrap',
          display:'flex',alignItems:'center',gap:5}}>
          <div style={{width:6,height:6,borderRadius:'50%',
            background:s.mode==='copy'?t.accent:t.warning}}/>
          {s.mode==='copy'?'复制':'移动'}
        </div>
      </div>
    );
  }

  return (
    <div style={{width:260,flexShrink:0,display:'flex',flexDirection:'column',
      background:t.panelBg,borderLeft:`1px solid ${t.border}`}}>
      <div style={{padding:'12px 16px',borderBottom:`1px solid ${t.border}`}}>
        <span style={{fontSize:11,fontWeight:600,color:t.textTer,textTransform:'uppercase',
          letterSpacing:'.08em'}}>分类类别</span>
      </div>
      <div style={{flex:1,overflowY:'auto',padding:'4px 0'}}>
        {s.cats.map(cat => {
          const fl = s.flash===cat.folder;
          const cnt = s.counts[cat.folder]||0;
          return (
            <div key={cat.key} onClick={()=>s.classify(cat.folder)} style={{
              display:'flex',alignItems:'center',gap:10,padding:'9px 16px',
              background:fl?`${cat.color}18`:'transparent',
              borderLeft:fl?`3px solid ${cat.color}`:'3px solid transparent',
              transition:'all .2s',cursor:'pointer',
            }}>
              <div style={{width:10,height:10,borderRadius:'50%',background:cat.color,flexShrink:0}}/>
              <span style={{display:'inline-flex',alignItems:'center',justifyContent:'center',
                minWidth:24,height:22,borderRadius:4,background:t.surfaceHover,
                fontSize:12,fontWeight:600,color:t.textSec,fontFamily:'monospace',
                padding:'0 5px'}}>{cat.key}</span>
              <span style={{flex:1,fontSize:13,color:t.text,fontWeight:500}}>{cat.display}</span>
              <span style={{fontSize:12,color:t.textTer,fontFamily:'monospace',
                minWidth:20,textAlign:'right'}}>{cnt}</span>
            </div>
          );
        })}
      </div>
      <div style={{padding:'10px 16px',borderTop:`1px solid ${t.border}`,
        display:'flex',alignItems:'center',gap:8}}>
        <div style={{width:8,height:8,borderRadius:'50%',
          background:s.mode==='copy'?t.accent:t.warning}}/>
        <span style={{fontSize:12,color:t.textSec}}>
          {s.mode==='copy'?'复制模式':'移动模式'}
        </span>
        <div style={{flex:1}}/>
        <span style={{fontSize:11,color:t.textTer,fontFamily:'monospace'}}>
          {s.mode==='copy'?'Ctrl+C':'Ctrl+X'}
        </span>
      </div>
    </div>
  );
}

/* ── Status Bar ── */
function StatusBar({ s }) {
  const t = _uc(ThemeCtx);
  const ok = s.screen==='classify';
  return (
    <div style={{
      display:'flex',alignItems:'center',padding:'0 12px',
      height:28,background:t.statusBg,borderTop:`1px solid ${t.border}`,
      fontSize:12,color:t.textSec,flexShrink:0,gap:8,
      fontVariantNumeric:'tabular-nums',userSelect:'none',
    }}>
      {ok ? (
        <>
          <span style={{display:'flex',alignItems:'center',gap:4}}>
            <MI.Undo size={11}/> {s.undos.length}
          </span>
          <span style={{width:1,height:14,background:t.border}}/>
          <span style={{fontWeight:600,color:t.text}}>{s.idx+1}/{s.total}</span>
          <span style={{color:t.textTer}}>·</span>
          <span style={{fontFamily:'monospace',fontSize:11}}>{s.img?.name}</span>
          <div style={{flex:1}}/>
          <span>已分类 <span style={{color:t.accent,fontWeight:600}}>{s.clsCount}</span>/{s.total}</span>
          <span style={{width:1,height:14,background:t.border}}/>
          <span style={{color:t.textTer,fontFamily:'monospace',fontSize:10,maxWidth:220,
            overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
            /Users/demo/datasets/animals/
          </span>
        </>
      ) : (
        <span style={{color:t.textTer}}>就绪 — 请打开图片文件夹开始工作</span>
      )}
    </div>
  );
}

Object.assign(window, { ToolBtn, ToolSep, MagpieToolbar, ImageViewer, CategoryPanel, StatusBar });

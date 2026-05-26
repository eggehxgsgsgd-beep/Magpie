// Magpie UI — Toolbar, ImageViewer, CategoryPanel, StatusBar
const { useState: _us, useEffect: _ue, useCallback: _ucb, useContext: _uc, useRef: _ur } = React;

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
      <ToolBtn icon={<MI.Folder/>} label="打开文件夹 (Ctrl+O)" onClick={()=>s.openFolder()}/>
      <ToolSep/>
      <ToolBtn icon={<MI.Left/>} label="上一张 (←)" onClick={s.prev} disabled={!ok||s.idx===0}/>
      <ToolBtn icon={<MI.Right/>} label="下一张 (→)" onClick={s.next} disabled={!ok||s.idx>=s.total-1}/>
      <ToolBtn icon={s.playing?<MI.Pause/>:<MI.Play/>} label="自动播放 (Space)"
        onClick={()=>s.setPlaying(!s.playing)} toggled={s.playing} disabled={!ok}/>
      <ToolBtn icon={<MI.Jump/>} label="跳转 (Ctrl+G)" onClick={()=>s.setJump(true)} disabled={!ok}/>
      <ToolSep/>
      <ToolBtn icon={<MI.Undo/>} label={`撤销 (Ctrl+Z) [${s.undos}]`} onClick={s.undo} disabled={!s.undos}/>
      <ToolBtn icon={<MI.Redo/>} label={`重做 (Ctrl+Y) [${s.redos}]`} onClick={s.redo} disabled={!s.redos}/>
      <ToolSep/>
      <ToolBtn
        icon={s.mode==='copy'?<MI.Copy/>:<MI.Move/>}
        label={s.mode==='copy'?'复制模式 (点击切换)':'移动模式 (点击切换)'}
        onClick={()=>s.setMode(m=>m==='copy'?'move':'copy')}
        toggled={s.mode==='move'} disabled={!ok}/>
      <ToolSep/>
      <ToolBtn icon={<MI.Fit/>} label="适应窗口 (F)" onClick={s.fitToWindow} disabled={!ok}/>
      <ToolBtn icon={<MI.ZoomIn/>} label="放大 (+)" onClick={s.zoomIn} disabled={!ok}/>
      <ToolBtn icon={<MI.ZoomOut/>} label="缩小 (-)" onClick={s.zoomOut} disabled={!ok}/>
      <ToolBtn icon={<MI.BBox/>} label="BBox 显示 (B)" onClick={()=>s.setBBox(!s.bbox)} toggled={s.bbox} disabled={!ok}/>
      <div style={{flex:1}}/>
      <ToolBtn icon={<MI.Tune/>} label="设置 (Ctrl+,)" onClick={()=>s.setSettings(true)}/>
    </div>
  );
}

function ImageViewer({ s, tweaks }) {
  const t = _uc(ThemeCtx);
  const img = s.img;
  const containerRef = _ur(null);
  const dragRef = _ur(null);
  const [containerSize, setContainerSize] = _us({ w: 0, h: 0 });
  const [dragging, setDragging] = _us(false);

  _ue(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const r = entries[0].contentRect;
      setContainerSize({ w: r.width, h: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const z = s.zoom;
  const iw = img?.w || 4032, ih = img?.h || 3024;
  const pad = 40;
  const fitScale = containerSize.w && containerSize.h
    ? Math.min((containerSize.w - pad) / iw, (containerSize.h - pad) / ih)
    : 0.2;
  if (s.fitScaleRef) s.fitScaleRef.current = fitScale;

  _ue(() => {
    if (!dragging) return;
    const move = (e) => {
      if (!dragRef.current) return;
      const d = dragRef.current;
      s.setZoom(prev => ({
        ...prev,
        mode: prev.mode === 'fit' ? 'custom' : prev.mode,
        scale: prev.mode === 'fit' ? fitScale : prev.mode === 'actual' ? 1 : prev.scale,
        panX: d.panX + (e.clientX - d.x),
        panY: d.panY + (e.clientY - d.y),
      }));
    };
    const up = () => { dragRef.current = null; setDragging(false); };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
    return () => { window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up); };
  }, [dragging, fitScale, s.setZoom]);

  if (!img) return <div ref={containerRef} style={{flex:1,background:t.viewerBg}}/>;

  const cats = s.cats;
  const imgCls = s.record[img.name];
  const lastFolder = imgCls?.[imgCls.length-1];
  const cat = lastFolder && cats.find(c => c.folder_name === lastFolder);
  const showBoxes = s.bbox ? (s.boxes || []) : [];
  s.fitScaleRef.current = fitScale;

  const scale = z.mode === 'fit' ? fitScale : z.mode === 'actual' ? 1 : z.scale;
  const dispW = iw * scale, dispH = ih * scale;
  const canPan = dispW > containerSize.w - 8 || dispH > containerSize.h - 8 || z.mode === 'custom';
  const zoomPct = Math.round(scale / fitScale * 100);

  const zoomAt = (clientX, clientY, factor) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const cx = rect.width / 2, cy = rect.height / 2;
    const mx = clientX - rect.left, my = clientY - rect.top;
    const cur = z.mode === 'fit' ? fitScale : z.mode === 'actual' ? 1 : z.scale;
    const next = Math.min(32, Math.max(0.02, cur * factor));
    const imgX = (mx - cx - z.panX) / cur;
    const imgY = (my - cy - z.panY) / cur;
    const panX = mx - cx - imgX * next;
    const panY = my - cy - imgY * next;
    if (next <= fitScale * 1.02 && factor < 1) {
      s.setZoom({ mode: 'fit', scale: 1, panX: 0, panY: 0 });
    } else {
      s.setZoom({ mode: 'custom', scale: next, panX, panY });
    }
  };

  const onWheel = (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
    zoomAt(e.clientX, e.clientY, factor);
  };

  const onMouseDown = (e) => {
    if (e.button !== 0) return;
    dragRef.current = { x: e.clientX, y: e.clientY, panX: z.panX, panY: z.panY };
    setDragging(true);
  };

  return (
    <div ref={containerRef}
      onWheel={onWheel}
      onMouseDown={onMouseDown}
      style={{
        flex:1, position:'relative', overflow:'hidden', minWidth:0,
        background:t.viewerBg, cursor: dragging ? 'grabbing' : canPan ? 'grab' : 'default',
      }}>
      <div style={{
        position:'absolute', left:'50%', top:'50%',
        transform:`translate(calc(-50% + ${z.panX}px), calc(-50% + ${z.panY}px))`,
        width:dispW, height:dispH,
        boxShadow:'0 4px 24px rgba(0,0,0,0.4)',
        borderRadius:2, overflow:'hidden', background:'#000',
        animation: z.mode === 'fit' ? 'imgIn .18s ease-out' : undefined,
      }}>
        {s.imgData ? (
          <img src={s.imgData} alt={img.name}
            style={{width:'100%',height:'100%',display:'block',objectFit:'fill',
              userSelect:'none',pointerEvents:'none'}}
            draggable={false}/>
        ) : s.imgLoading ? (
          <div style={{position:'absolute',inset:0,display:'flex',alignItems:'center',justifyContent:'center',
            color:'rgba(255,255,255,0.6)',fontSize:12,fontFamily:'monospace'}}>加载中…</div>
        ) : (
          <div style={{position:'absolute',inset:0,display:'flex',alignItems:'center',justifyContent:'center',
            color:'rgba(255,255,255,0.4)',fontSize:12,fontFamily:'monospace'}}>{img.name}</div>
        )}

        {showBoxes.map((box, i) => {
          const catIdx = box.cls ?? 0;
          const bc = cats[catIdx]?.color || '#78716C';
          const bl = cats[catIdx]?.display_name || cats[catIdx]?.folder_name || `class ${catIdx}`;
          return (
            <div key={i} style={{
              position:'absolute',
              left:`${(box.cx-box.w/2)*100}%`, top:`${(box.cy-box.h/2)*100}%`,
              width:`${box.w*100}%`, height:`${box.h*100}%`,
              border:`2px solid ${bc}`, background:`${bc}15`, borderRadius:2,
              pointerEvents:'none',
            }}>
              <span style={{
                position:'absolute', top:-22, left:-2,
                background:bc, color:'#fff', padding:'2px 7px',
                fontSize:11, fontWeight:600, borderRadius:3,
                whiteSpace:'nowrap', lineHeight:'16px',
              }}>{bl}{typeof box.cf === 'number' ? ` ${box.cf.toFixed(2)}` : ''}</span>
            </div>
          );
        })}
      </div>

      {imgCls && cat && (
        tweaks.badgeStyle==='tag' ? (
          <div style={{position:'absolute',top:12,left:12,pointerEvents:'none',
            background:cat.color, padding:'4px 14px', borderRadius:4}}>
            <span style={{fontSize:12,color:'#fff',fontWeight:600}}>{cat.display_name || cat.folder_name}</span>
          </div>
        ) : (
          <div style={{position:'absolute',top:12,left:12,display:'flex',alignItems:'center',gap:6,
            pointerEvents:'none', background:'rgba(0,0,0,0.7)',backdropFilter:'blur(8px)',
            padding:'5px 12px',borderRadius:6,border:`1px solid ${cat.color}40`}}>
            <div style={{width:8,height:8,borderRadius:'50%',background:cat.color}}/>
            <span style={{fontSize:12,color:'#fff',fontWeight:500}}>已分类: {cat.display_name || cat.folder_name}</span>
          </div>
        )
      )}

      <div style={{position:'absolute',bottom:12,right:12,display:'flex',alignItems:'center',gap:10,
        fontSize:11,color:'rgba(255,255,255,0.45)',fontFamily:'monospace',pointerEvents:'none'}}>
        <span>{zoomPct}%</span>
        {img.w && img.h && <span>{img.w}×{img.h}</span>}
        <span style={{opacity:0.7}}>
          {z.mode === 'fit' ? '适应窗口' : z.mode === 'actual' ? '1:1' : '自定义'}
        </span>
      </div>

      {s.playing && (
        <div style={{position:'absolute',top:12,right:12,display:'flex',alignItems:'center',gap:5,
          pointerEvents:'none', background:'rgba(0,0,0,0.6)',backdropFilter:'blur(8px)',
          padding:'4px 10px',borderRadius:6}}>
          <div style={{width:6,height:6,borderRadius:'50%',background:'#EF4444',
            animation:'pulse 1s infinite'}}/>
          <span style={{fontSize:11,color:'rgba(255,255,255,0.7)',fontWeight:500}}>自动播放中</span>
        </div>
      )}
    </div>
  );
}

function CategoryPanel({ s, tweaks }) {
  const t = _uc(ThemeCtx);
  const isBottom = tweaks.layout==='bottom';
  const cats = s.cats;

  if (cats.length === 0) {
    return (
      <div style={{width:260,display:'flex',flexDirection:'column',background:t.panelBg,
        borderLeft:`1px solid ${t.border}`,padding:'18px 16px',color:t.textSec,fontSize:13,
        lineHeight:1.6}}>
        <div style={{fontSize:11,fontWeight:600,color:t.textTer,textTransform:'uppercase',
          letterSpacing:'.08em',marginBottom:12}}>分类类别</div>
        尚未配置类别。<br/>请点击工具栏 <b style={{color:t.text}}>设置</b> → <b style={{color:t.text}}>类别</b> 添加。
      </div>
    );
  }

  if (isBottom) {
    return (
      <div style={{display:'flex',alignItems:'center',gap:6,padding:'0 12px',
        height:50,background:t.panelBg,borderTop:`1px solid ${t.border}`,
        flexShrink:0,overflowX:'auto'}}>
        {cats.map(cat => {
          const fl = s.flash===cat.folder_name;
          const cnt = s.counts[cat.folder_name]||0;
          return (
            <div key={cat.key+cat.folder_name} onClick={()=>s.classify(cat.folder_name)} style={{
              display:'flex',alignItems:'center',gap:6,padding:'6px 14px',
              borderRadius:6,background:fl?`${cat.color}20`:'transparent',
              border:`1px solid ${fl?cat.color:t.border}`,
              transition:'all .2s',whiteSpace:'nowrap',cursor:'pointer',
            }}>
              <div style={{width:8,height:8,borderRadius:'50%',background:cat.color,flexShrink:0}}/>
              <span style={{display:'inline-flex',alignItems:'center',justifyContent:'center',
                width:20,height:20,borderRadius:4,background:t.surfaceHover,
                fontSize:11,fontWeight:600,color:t.textSec,fontFamily:'monospace'}}>{cat.key}</span>
              <span style={{fontSize:13,color:t.text,fontWeight:500}}>{cat.display_name || cat.folder_name}</span>
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
        {cats.map(cat => {
          const fl = s.flash===cat.folder_name;
          const cnt = s.counts[cat.folder_name]||0;
          return (
            <div key={cat.key+cat.folder_name} onClick={()=>s.classify(cat.folder_name)} style={{
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
              <span style={{flex:1,fontSize:13,color:t.text,fontWeight:500,
                whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>{cat.display_name || cat.folder_name}</span>
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
      </div>
    </div>
  );
}

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
            <MI.Undo size={11}/> {s.undos}
          </span>
          <span style={{width:1,height:14,background:t.border}}/>
          <span style={{fontWeight:600,color:t.text}}>{s.idx+1}/{s.total}</span>
          <span style={{color:t.textTer}}>·</span>
          <span style={{fontFamily:'monospace',fontSize:11,maxWidth:260,
            overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{s.img?.name}</span>
          <div style={{flex:1}}/>
          <span>已分类 <span style={{color:t.accent,fontWeight:600}}>{s.classifiedCount}</span>/{s.total}</span>
          <span style={{width:1,height:14,background:t.border}}/>
          <span style={{color:t.textTer,fontFamily:'monospace',fontSize:10,maxWidth:340,
            overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',direction:'rtl'}}
            title={s.folder}>
            {s.folder}
          </span>
        </>
      ) : (
        <span style={{color:t.textTer}}>就绪 — 请打开图片文件夹开始工作</span>
      )}
    </div>
  );
}

Object.assign(window, { ToolBtn, ToolSep, MagpieToolbar, ImageViewer, CategoryPanel, StatusBar });

// Magpie — Data layer, themes, state management
const { useState, useEffect, useCallback, useMemo, useRef, createContext } = React;

const ThemeCtx = createContext(null);

const THEMES = {
  dark: {
    name:'dark', bg:'#18181B', surface:'#27272A', surfaceHover:'#3F3F46',
    surfaceActive:'#52525B', border:'#3F3F46', borderLight:'#52525B',
    text:'#FAFAFA', textSec:'#A1A1AA', textTer:'#71717A',
    accent:'#22D3EE', accentHover:'#06B6D4', accentBg:'rgba(34,211,238,0.12)',
    danger:'#EF4444', dangerBg:'rgba(239,68,68,0.1)',
    success:'#22C55E', warning:'#F59E0B',
    viewerBg:'#09090B', toolbarBg:'#27272A', toolbarBorder:'#3F3F46',
    statusBg:'#1E1E22', panelBg:'#1F1F23',
    dialogBg:'#27272A', backdrop:'rgba(0,0,0,0.6)',
    toastBg:'#3F3F46', toastText:'#FAFAFA',
    inputBg:'#18181B', inputBorder:'#3F3F46',
  },
  light: {
    name:'light', bg:'#F4F4F5', surface:'#FFFFFF', surfaceHover:'#F4F4F5',
    surfaceActive:'#E4E4E7', border:'#E4E4E7', borderLight:'#D4D4D8',
    text:'#18181B', textSec:'#71717A', textTer:'#A1A1AA',
    accent:'#0891B2', accentHover:'#0E7490', accentBg:'rgba(8,145,178,0.08)',
    danger:'#DC2626', dangerBg:'rgba(220,38,38,0.08)',
    success:'#16A34A', warning:'#D97706',
    viewerBg:'#27272A', toolbarBg:'#FFFFFF', toolbarBorder:'#E4E4E7',
    statusBg:'#FFFFFF', panelBg:'#FAFAFA',
    dialogBg:'#FFFFFF', backdrop:'rgba(0,0,0,0.3)',
    toastBg:'#18181B', toastText:'#FAFAFA',
    inputBg:'#F4F4F5', inputBorder:'#E4E4E7',
  }
};

const CAT_COLORS = [
  '#22C55E','#3B82F6','#F59E0B','#EF4444','#A855F7',
  '#EC4899','#14B8A6','#F97316','#6366F1','#84CC16','#06B6D4','#78716C'
];

const DEF_CATS = [
  { key:'1', folder:'cat', display:'猫', color:CAT_COLORS[0] },
  { key:'2', folder:'dog', display:'狗', color:CAT_COLORS[1] },
  { key:'3', folder:'bird', display:'鸟', color:CAT_COLORS[2] },
  { key:'4', folder:'fish', display:'鱼', color:CAT_COLORS[3] },
  { key:'5', folder:'other', display:'其他', color:CAT_COLORS[4] },
];

const IMAGES = [
  { id:0, name:'IMG_0421.jpg', grad:['#5a3a1a','#b8860b'], label:'橘猫特写', w:3024, h:4032 },
  { id:1, name:'IMG_0422.jpg', grad:['#1e3a5f','#4682b4'], label:'金毛犬户外', w:4032, h:3024 },
  { id:2, name:'IMG_0423.jpg', grad:['#1a3c2a','#3a8a5c'], label:'树枝上的喜鹊', w:3024, h:4032 },
  { id:3, name:'IMG_0424.jpg', grad:['#3a1a4a','#7b3f9e'], label:'白猫侧面', w:4032, h:3024 },
  { id:4, name:'IMG_0425.jpg', grad:['#0d1b2a','#1b4f72'], label:'锦鲤池塘', w:4032, h:3024 },
  { id:5, name:'IMG_0426.jpg', grad:['#4a1a3a','#9b59b6'], label:'柴犬微笑', w:3024, h:3024 },
  { id:6, name:'IMG_0427.jpg', grad:['#2a3a10','#6b8e23'], label:'飞行中的白鹭', w:6000, h:4000 },
  { id:7, name:'IMG_0428.jpg', grad:['#3a1a0a','#8b4513'], label:'黑猫夜景', w:3024, h:4032 },
  { id:8, name:'IMG_0429.jpg', grad:['#2d2d2d','#5a5a5a'], label:'模糊的照片', w:2048, h:1536 },
  { id:9, name:'IMG_0430.jpg', grad:['#0f1f3d','#2c5f8a'], label:'海底珊瑚鱼', w:4032, h:3024 },
];

const BBOXES = {
  0: [{ cls:0, cx:.48, cy:.42, w:.55, h:.65, cf:.96 }],
  2: [{ cls:2, cx:.35, cy:.30, w:.22, h:.28, cf:.91 },{ cls:2, cx:.72, cy:.58, w:.18, h:.22, cf:.73 }],
  4: [{ cls:3, cx:.45, cy:.52, w:.50, h:.30, cf:.89 },{ cls:3, cx:.78, cy:.35, w:.15, h:.18, cf:.62 }],
  6: [{ cls:2, cx:.55, cy:.35, w:.30, h:.40, cf:.84 }],
  7: [{ cls:0, cx:.42, cy:.48, w:.40, h:.55, cf:.78 },{ cls:1, cx:.80, cy:.65, w:.15, h:.20, cf:.34 }],
};

function useMagpie() {
  const [screen, setScreen] = useState('welcome');
  const [idx, setIdx] = useState(0);
  const [cats, setCats] = useState(DEF_CATS);
  const [cls, setCls] = useState({ 0:['cat'], 1:['dog'], 2:['bird'] });
  const [undos, setUndos] = useState([]);
  const [redos, setRedos] = useState([]);
  const [playing, setPlaying] = useState(false);
  const [bbox, setBBox] = useState(true);
  const [mode, setMode] = useState('copy');
  const [toast, setToast] = useState(null);
  const [settings, setSettings] = useState(false);
  const [conflict, setConflict] = useState(null);
  const [jump, setJump] = useState(false);
  const [flash, setFlash] = useState(null);

  const toastT = useRef(null);
  const playT = useRef(null);
  const flashT = useRef(null);

  const img = IMAGES[idx];
  const total = IMAGES.length;
  const clsCount = Object.keys(cls).length;

  const counts = useMemo(() => {
    const c = {};
    cats.forEach(ct => c[ct.folder] = 0);
    Object.values(cls).forEach(arr => arr.forEach(f => { if(c[f]!==undefined) c[f]++; }));
    return c;
  }, [cls, cats]);

  const showToast = useCallback((msg, color) => {
    clearTimeout(toastT.current);
    setToast({ msg, color });
    toastT.current = setTimeout(() => setToast(null), 2000);
  }, []);

  const doFlash = useCallback((folder) => {
    clearTimeout(flashT.current);
    setFlash(folder);
    flashT.current = setTimeout(() => setFlash(null), 400);
  }, []);

  const next = useCallback(() => { setIdx(i => Math.min(i+1, IMAGES.length-1)); }, []);
  const prev = useCallback(() => { setIdx(i => Math.max(i-1, 0)); }, []);
  const goTo = useCallback((n) => { setIdx(Math.max(0, Math.min(n, IMAGES.length-1))); }, []);

  const classify = useCallback((folder) => {
    const cat = cats.find(c => c.folder === folder);
    if (!cat) return;
    doFlash(folder);
    if (cls[idx]?.includes(folder)) {
      setConflict({ imgId:idx, cat });
      return;
    }
    setCls(p => ({ ...p, [idx]: [...(p[idx]||[]), folder] }));
    setUndos(s => [...s.slice(-99), { imgId:idx, folder, i:idx }]);
    setRedos([]);
    showToast(`已分类到 ${cat.display}`, cat.color);
    if (idx < IMAGES.length - 1) setTimeout(next, 120);
  }, [cats, idx, cls, next, showToast, doFlash]);

  const undo = useCallback(() => {
    if (!undos.length) return;
    const last = undos[undos.length-1];
    setUndos(s => s.slice(0,-1));
    setRedos(s => [...s, last]);
    setCls(p => {
      const arr = [...(p[last.imgId]||[])];
      const i = arr.lastIndexOf(last.folder);
      if(i>=0) arr.splice(i,1);
      const n = {...p};
      if(!arr.length) delete n[last.imgId]; else n[last.imgId] = arr;
      return n;
    });
    setPlaying(false);
    setIdx(last.i);
    showToast('已撤销', '#71717A');
  }, [undos, showToast]);

  const redo = useCallback(() => {
    if (!redos.length) return;
    const last = redos[redos.length-1];
    setRedos(s => s.slice(0,-1));
    setUndos(s => [...s, last]);
    setCls(p => ({ ...p, [last.imgId]: [...(p[last.imgId]||[]), last.folder] }));
    const cat = cats.find(c => c.folder === last.folder);
    showToast(`重做: ${cat?.display||last.folder}`, cat?.color||'#71717A');
  }, [redos, cats, showToast]);

  const resolveConflict = useCallback((action) => {
    if (!conflict) return;
    const { imgId, cat } = conflict;
    setConflict(null);
    if (action==='cancel'||action==='skip') return;
    setCls(p => ({ ...p, [imgId]: [...(p[imgId]||[]), cat.folder] }));
    setUndos(s => [...s.slice(-99), { imgId, folder:cat.folder, i:idx }]);
    setRedos([]);
    const label = action==='rename' ? `已重命名并分类到 ${cat.display}` : `已覆盖分类到 ${cat.display}`;
    showToast(label, cat.color);
    if (idx < IMAGES.length-1) setTimeout(next, 120);
  }, [conflict, idx, next, showToast]);

  useEffect(() => {
    if (playing) {
      playT.current = setInterval(() => {
        setIdx(i => { if(i>=IMAGES.length-1){setPlaying(false);return i;} return i+1; });
      }, 800);
    }
    return () => clearInterval(playT.current);
  }, [playing]);

  const openFolder = useCallback(() => { setScreen('classify'); setIdx(0); }, []);

  return {
    screen, setScreen, idx, img, total, cats, setCats,
    cls, clsCount, counts, undos, redos,
    playing, setPlaying, bbox, setBBox,
    mode, setMode, toast, settings, setSettings,
    conflict, resolveConflict, jump, setJump, flash,
    next, prev, goTo, classify, undo, redo, openFolder,
  };
}

Object.assign(window, { ThemeCtx, THEMES, CAT_COLORS, DEF_CATS, IMAGES, BBOXES, useMagpie });

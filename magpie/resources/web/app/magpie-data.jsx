// Magpie — Data layer & state (wired to Python backend via window.magpieApi)
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

const SUPPORTED_EXTS = ['jpg','jpeg','png','bmp','webp','tiff','gif','svg'];

const DEFAULT_PREFS = {
  categories: [],
  source_dir: '',
  output_dir: '',
  labels_dir: '',
  classes_path: '',
  autoplay_interval_ms: 100,
  show_bboxes: true,
  show_classified_marker: true,
  theme: 'system',
  default_operation: 'copy',
  undo_prompt: false,
  end_behavior: 'stay',
  file_extensions: ['jpg','jpeg','png','bmp','webp','tiff'],
  conflict_strategy: 'ask',
  sort_strategy: 'natural',
  recursive_scan: false,
  remember_recursive_scan: false,
};

// Resolve "system" preference to a concrete theme key honoring OS dark mode.
function resolveTheme(themePref) {
  if (themePref === 'dark' || themePref === 'light') return themePref;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function useMagpie(api) {
  const [screen, setScreen] = useState('welcome');
  const [idx, setIdx] = useState(0);
  const [images, setImages] = useState([]);
  const [folder, setFolder] = useState('');
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);
  const [record, setRecord] = useState({}); // { imageName: [folderName, ...] }
  const [undos, setUndos] = useState(0);
  const [redos, setRedos] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [bbox, setBBox] = useState(true);
  const [mode, setMode] = useState('copy');
  const [toast, setToast] = useState(null);
  const [settings, setSettings] = useState(false);
  const [conflict, setConflict] = useState(null);
  const [jump, setJump] = useState(false);
  const [flash, setFlash] = useState(null);
  const [imgData, setImgData] = useState(null);
  const [imgLoading, setImgLoading] = useState(false);
  const [boxes, setBoxes] = useState([]);

  const toastT = useRef(null);
  const playT = useRef(null);
  const flashT = useRef(null);
  const imgReq = useRef(0);

  const img = images[idx];
  const total = images.length;

  const cats = prefs.categories || [];
  const classifiedCount = Object.keys(record).length;

  const counts = useMemo(() => {
    const c = {};
    cats.forEach(ct => c[ct.folder_name] = 0);
    Object.values(record).forEach(arr => arr.forEach(f => { if(c[f]!==undefined) c[f]++; }));
    return c;
  }, [record, cats]);

  const showToast = useCallback((msg, color) => {
    clearTimeout(toastT.current);
    setToast({ msg, color: color || '#71717A' });
    toastT.current = setTimeout(() => setToast(null), 2000);
  }, []);

  const doFlash = useCallback((folderName) => {
    clearTimeout(flashT.current);
    setFlash(folderName);
    flashT.current = setTimeout(() => setFlash(null), 400);
  }, []);

  const next = useCallback(() => { setIdx(i => Math.min(i+1, Math.max(images.length-1, 0))); }, [images.length]);
  const prev = useCallback(() => { setIdx(i => Math.max(i-1, 0)); }, []);
  const goTo = useCallback((n) => { setIdx(Math.max(0, Math.min(n, Math.max(images.length-1, 0)))); }, [images.length]);

  const loadImage = useCallback(async (path) => {
    if (!api || !path) { setImgData(null); setBoxes([]); return; }
    const reqId = ++imgReq.current;
    setImgLoading(true);
    try {
      const res = await api.getImageData(path);
      if (reqId !== imgReq.current) return;
      if (res && res.ok) {
        setImgData(res.dataUrl);
        setBoxes(res.boxes || []);
      } else {
        setImgData(null); setBoxes([]);
        showToast(res && res.error ? `加载失败: ${res.error}` : '图像加载失败', '#EF4444');
      }
    } catch (err) {
      console.error(err);
      if (reqId === imgReq.current) { setImgData(null); setBoxes([]); }
    } finally {
      if (reqId === imgReq.current) setImgLoading(false);
    }
  }, [api, showToast]);

  useEffect(() => { if (img && img.path) loadImage(img.path); else { setImgData(null); setBoxes([]); } }, [img, loadImage]);

  const applyFolderResult = useCallback((res) => {
    if (!res || !res.ok) return false;
    setImages(res.images || []);
    setFolder(res.folder || '');
    setRecord(res.record || {});
    setUndos(0); setRedos(0);
    setScreen('classify');
    setIdx(0);
    return true;
  }, []);

  const openFolder = useCallback(async (path) => {
    if (!api) return;
    let target = path;
    if (!target) {
      const picked = await api.pickFolder('source');
      if (!picked || !picked.path) return;
      target = picked.path;
    }
    const res = await api.loadImageFolder(target);
    if (res && res.needs_recursive_prompt) {
      const ok = window.confirm('所选目录包含子目录，是否递归扫描子目录中的图片？\n\n确定 = 递归扫描，取消 = 仅当前目录');
      const remember = window.confirm('是否记住此选择，下次自动应用？');
      const res2 = await api.confirmRecursive(target, ok, remember);
      applyFolderResult(res2);
    } else if (res && res.ok) {
      applyFolderResult(res);
    } else if (res && res.error) {
      showToast(res.error, '#EF4444');
    }
  }, [api, applyFolderResult, showToast]);

  const classify = useCallback(async (folderName, conflictAction, remember) => {
    const cat = cats.find(c => c.folder_name === folderName);
    if (!cat || !img || !api) return;
    doFlash(folderName);
    const res = await api.classifyImage(img.path, folderName, mode, conflictAction || '', !!remember);
    if (!res) return;
    if (res.conflict) {
      setConflict({ imgPath: img.path, cat, target: res.target });
      return;
    }
    setConflict(null);
    if (res.ok) {
      setRecord(p => {
        const arr = [...(p[img.name] || [])];
        if (!arr.includes(folderName)) arr.push(folderName);
        return { ...p, [img.name]: arr };
      });
      setUndos(res.undos ?? (undos + 1));
      setRedos(0);
      if (res.removed) {
        setImages(curr => {
          const next = curr.filter(it => it.path !== img.path);
          if (next.length === 0) { setScreen('welcome'); return next; }
          setIdx(i => Math.min(i, next.length - 1));
          return next;
        });
      } else if (idx < images.length - 1) {
        setTimeout(() => next(), 120);
      }
      showToast(res.message || `已分类到 ${cat.display_name || cat.folder_name}`, cat.color);
    } else if (res.skipped) {
      showToast('已跳过', '#71717A');
    } else if (res.error) {
      showToast(res.error, '#EF4444');
    }
  }, [cats, img, mode, api, idx, images.length, next, showToast, doFlash, undos]);

  const undo = useCallback(async () => {
    if (!api) return;
    const res = await api.undo();
    if (!res || !res.ok) return;
    setPlaying(false);
    setUndos(res.undos ?? Math.max(undos - 1, 0));
    setRedos(res.redos ?? (redos + 1));
    if (res.record) setRecord(res.record);
    if (res.images) setImages(res.images);
    if (typeof res.index === 'number') setIdx(res.index);
    showToast('已撤销', '#71717A');
  }, [api, undos, redos, showToast]);

  const redo = useCallback(async () => {
    if (!api) return;
    const res = await api.redo();
    if (!res || !res.ok) return;
    setUndos(res.undos ?? (undos + 1));
    setRedos(res.redos ?? Math.max(redos - 1, 0));
    if (res.record) setRecord(res.record);
    if (res.images) setImages(res.images);
    if (typeof res.index === 'number') setIdx(res.index);
    const cat = cats.find(c => c.folder_name === res.folder);
    showToast(`重做: ${cat?.display_name || res.folder || ''}`, cat?.color || '#71717A');
  }, [api, undos, redos, cats, showToast]);

  const resolveConflict = useCallback((action, remember) => {
    if (!conflict) return;
    const folderName = conflict.cat.folder_name;
    setConflict(null);
    if (action === 'cancel' || action === 'skip') {
      showToast(action === 'skip' ? '已跳过' : '已取消', '#71717A');
      return;
    }
    classify(folderName, action, remember);
  }, [conflict, classify, showToast]);

  useEffect(() => {
    if (playing) {
      const interval = Math.max(50, prefs.autoplay_interval_ms || 100);
      playT.current = setInterval(() => {
        setIdx(i => {
          if (i >= images.length - 1) {
            if (prefs.end_behavior === 'loop') return 0;
            setPlaying(false);
            return i;
          }
          return i + 1;
        });
      }, interval);
    }
    return () => clearInterval(playT.current);
  }, [playing, prefs.autoplay_interval_ms, prefs.end_behavior, images.length]);

  const refreshPrefs = useCallback(async () => {
    if (!api) return;
    const res = await api.getPreferences();
    if (res) {
      setPrefs(res);
      setMode(res.default_operation || 'copy');
      setBBox(!!res.show_bboxes);
    }
  }, [api]);

  // Image viewer zoom/pan — mode: fit | actual | custom
  const [zoom, setZoom] = useState({ mode: 'fit', scale: 1, panX: 0, panY: 0 });
  const fitScaleRef = useRef(1);

  useEffect(() => {
    setZoom({ mode: 'fit', scale: 1, panX: 0, panY: 0 });
  }, [img?.path]);

  const fitToWindow = useCallback(() => {
    setZoom({ mode: 'fit', scale: 1, panX: 0, panY: 0 });
  }, []);

  const actualSize = useCallback(() => {
    setZoom({ mode: 'actual', scale: 1, panX: 0, panY: 0 });
  }, []);

  const zoomIn = useCallback(() => {
    setZoom(z => {
      const cur = z.mode === 'fit' ? fitScaleRef.current : z.mode === 'actual' ? 1 : z.scale;
      return { mode: 'custom', scale: Math.min(32, cur * 1.25), panX: z.panX, panY: z.panY };
    });
  }, []);

  const zoomOut = useCallback(() => {
    setZoom(z => {
      const cur = z.mode === 'fit' ? fitScaleRef.current : z.mode === 'actual' ? 1 : z.scale;
      const next = Math.max(0.02, cur / 1.25);
      if (next <= fitScaleRef.current * 1.02) {
        return { mode: 'fit', scale: 1, panX: 0, panY: 0 };
      }
      return { mode: 'custom', scale: next, panX: z.panX, panY: z.panY };
    });
  }, []);

  return {
    screen, setScreen, idx, img, total, images, folder,
    cats, prefs, setPrefs, record, refreshPrefs,
    undos, redos, classifiedCount, counts,
    playing, setPlaying, bbox, setBBox,
    mode, setMode, toast, settings, setSettings,
    conflict, resolveConflict, jump, setJump, flash,
    next, prev, goTo, classify, undo, redo, openFolder,
    imgData, imgLoading, boxes, showToast,
    zoom, setZoom, fitScaleRef, fitToWindow, actualSize, zoomIn, zoomOut,
  };
}

Object.assign(window, { ThemeCtx, THEMES, CAT_COLORS, SUPPORTED_EXTS, DEFAULT_PREFS, resolveTheme, useMagpie });

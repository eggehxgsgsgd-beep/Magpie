// Magpie Icons — Linear style, 18×18 viewBox
const Ic = ({children, size=18, ...p}) => (
  <svg width={size} height={size} viewBox="0 0 18 18" fill="none" stroke="currentColor"
    strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}>{children}</svg>
);

const MI = {};

MI.Folder = ({size=18,...p}) => <Ic size={size} {...p}><path d="M2 13V5a1 1 0 011-1h3l2 2h6a1 1 0 011 1v1"/><path d="M2 13l2.5-5H16l-2.5 5H2z"/></Ic>;
MI.Left = ({size=18,...p}) => <Ic size={size} {...p}><path d="M11 3L6 9l5 6"/></Ic>;
MI.Right = ({size=18,...p}) => <Ic size={size} {...p}><path d="M7 3l5 6-5 6"/></Ic>;
MI.Play = ({size=18,...p}) => <Ic size={size} {...p}><path d="M5 3v12l9-6z" fill="currentColor" stroke="none"/></Ic>;
MI.Pause = ({size=18,...p}) => <Ic size={size} {...p}><rect x="4" y="3" width="2.5" height="12" rx=".5" fill="currentColor" stroke="none"/><rect x="11.5" y="3" width="2.5" height="12" rx=".5" fill="currentColor" stroke="none"/></Ic>;
MI.Jump = ({size=18,...p}) => <Ic size={size} {...p}><path d="M3 9h8M8 5l4 4-4 4"/><path d="M15 4v10"/></Ic>;
MI.Undo = ({size=18,...p}) => <Ic size={size} {...p}><path d="M4 7h6a3.5 3.5 0 010 7H8"/><path d="M7 4L4 7l3 3"/></Ic>;
MI.Redo = ({size=18,...p}) => <Ic size={size} {...p}><path d="M14 7H8a3.5 3.5 0 000 7h2"/><path d="M11 4l3 3-3 3"/></Ic>;
MI.Copy = ({size=18,...p}) => <Ic size={size} {...p}><rect x="6" y="6" width="9" height="9" rx="1.5"/><path d="M3 12.5V4a1.5 1.5 0 011.5-1.5H13"/></Ic>;
MI.Move = ({size=18,...p}) => <Ic size={size} {...p}><circle cx="5" cy="4.5" r="2"/><circle cx="5" cy="13.5" r="2"/><path d="M14 3L7 10.5M14 15L7 7.5"/></Ic>;
MI.Fit = ({size=18,...p}) => <Ic size={size} {...p}><path d="M2 6V2h4M12 2h4v4M2 12v4h4M16 12v4h-4"/></Ic>;
MI.ZoomIn = ({size=18,...p}) => <Ic size={size} {...p}><circle cx="7.5" cy="7.5" r="4.5"/><path d="M11 11l4 4M7.5 5v5M5 7.5h5"/></Ic>;
MI.ZoomOut = ({size=18,...p}) => <Ic size={size} {...p}><circle cx="7.5" cy="7.5" r="4.5"/><path d="M11 11l4 4M5 7.5h5"/></Ic>;
MI.BBox = ({size=18,...p}) => <Ic size={size} {...p}><path d="M2 5V2h3M13 2h3v3M2 13v3h3M16 13v3h-3"/><rect x="5" y="5" width="8" height="8" strokeDasharray="2 2"/></Ic>;
MI.Tune = ({size=18,...p}) => <Ic size={size} {...p}><circle cx="5" cy="5" r="1.5"/><circle cx="13" cy="9" r="1.5"/><circle cx="7" cy="13" r="1.5"/><path d="M6.5 5H16M2 5h1.5M14.5 9H16M2 9h10M8.5 13H16M2 13h3.5"/></Ic>;
MI.Close = ({size=18,...p}) => <Ic size={size} {...p}><path d="M4.5 4.5l9 9M13.5 4.5l-9 9"/></Ic>;
MI.Trash = ({size=18,...p}) => <Ic size={size} {...p}><path d="M3 5h12M7 5V3.5h4V5"/><path d="M5 5l.7 9.5a1 1 0 001 .9h4.6a1 1 0 001-.9L13 5"/></Ic>;
MI.Plus = ({size=18,...p}) => <Ic size={size} {...p}><path d="M9 3v12M3 9h12"/></Ic>;
MI.Check = ({size=18,...p}) => <Ic size={size} {...p}><path d="M3.5 9.5l4 4 7-8"/></Ic>;
MI.Alert = ({size=18,...p}) => <Ic size={size} {...p}><path d="M9 2L2 15h14L9 2z"/><path d="M9 7v4"/><circle cx="9" cy="13" r=".5" fill="currentColor"/></Ic>;
MI.Search = ({size=18,...p}) => <Ic size={size} {...p}><circle cx="7.5" cy="7.5" r="4.5"/><path d="M11 11l4.5 4.5"/></Ic>;
MI.Download = ({size=18,...p}) => <Ic size={size} {...p}><path d="M9 2v10M5 8l4 4 4-4M3 14h12"/></Ic>;
MI.Upload = ({size=18,...p}) => <Ic size={size} {...p}><path d="M9 12V2M5 6l4-4 4 4M3 14h12"/></Ic>;
MI.Grip = ({size=18,...p}) => <Ic size={size} {...p}><circle cx="6.5" cy="4" r=".8" fill="currentColor" stroke="none"/><circle cx="11.5" cy="4" r=".8" fill="currentColor" stroke="none"/><circle cx="6.5" cy="9" r=".8" fill="currentColor" stroke="none"/><circle cx="11.5" cy="9" r=".8" fill="currentColor" stroke="none"/><circle cx="6.5" cy="14" r=".8" fill="currentColor" stroke="none"/><circle cx="11.5" cy="14" r=".8" fill="currentColor" stroke="none"/></Ic>;
MI.Info = ({size=18,...p}) => <Ic size={size} {...p}><circle cx="9" cy="9" r="7"/><path d="M9 8v5M9 5.5v.5"/></Ic>;
MI.Keyboard = ({size=18,...p}) => <Ic size={size} {...p}><rect x="1" y="4" width="16" height="10" rx="1.5"/><path d="M4 7h2M8 7h2M12 7h2M5 10h8"/></Ic>;

MI.Logo = ({size=22}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <rect width="24" height="24" rx="5" fill="#0E7490"/>
    <text x="12" y="16.5" textAnchor="middle" fill="white" fontSize="14" fontWeight="700"
      fontFamily="-apple-system,system-ui,sans-serif">M</text>
  </svg>
);

Object.assign(window, { MI });

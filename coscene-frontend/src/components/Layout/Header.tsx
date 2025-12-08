/**
 * App Header Component
 */

interface HeaderProps {
  sessionId: string | null;
}

export function Header({ sessionId }: HeaderProps) {
  return null;
  // return (
    // <header className="bg-white border-b border-gray-200 px-6 py-3 flex-shrink-0">
    //   <div className="flex items-center justify-between" >
    //     <div>
    //       <h1 className="text-2xl font-semibold text-gray-900 tracking-tight"
    //       >CoScene</h1>
    //       {/* <p className="text-sm text-gray-500">Agentic 3D Scene Editing</p> */}
    //     </div>

    //     {/* {sessionId && (
    //       <div className="text-right">
    //         <div className="text-xs text-gray-400">Session ID</div>
    //         <div className="text-sm text-gray-600 font-mono">
    //           {sessionId.slice(0, 8)}...
    //         </div>
    //       </div>
    //     )} */}
    //   </div>
    // </header>
  // );
}

import React, { useState, useEffect } from "react";
import { Fade } from "@mui/material";

export default function PageFade({ children }) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Small delay to ensure DOM is ready before starting animation
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, 150);

    return () => clearTimeout(timer);
  }, []);

  // Safety check to ensure children exists
  if (!children) {
    return null;
  }
  
  return (
    <Fade 
      in={isVisible} 
      timeout={400}
      mountOnEnter
      unmountOnExit
    >
      <div style={{ width: '100%' }}>{children}</div>
    </Fade>
  );
}

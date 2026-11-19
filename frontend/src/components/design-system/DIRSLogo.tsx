import React from 'react';

export interface DIRSLogoProps {
  /**
   * Display variant determining the symbol's display dimensions:
   * - 'compact': ~32px height (for navbar & tight headers: 28–34px)
   * - 'standard': ~48px height (for section headers: 40–56px)
   * - 'large': ~72px height (for focus headers & splash: 64–84px)
   * - 'hero': ~96px height (for auth hero anchors: 90–120px)
   */
  variant?: 'compact' | 'standard' | 'large' | 'hero';
  /** Optional custom height in pixels */
  size?: number;
  className?: string;
  imageClassName?: string;
  alt?: string;
}

export const DIRSLogo: React.FC<DIRSLogoProps> = ({
  variant = 'standard',
  size,
  className = '',
  imageClassName = '',
  alt = 'DIRS Emergency Operations Symbol',
}) => {
  const logoSrc = '/assets/dirs-logo.png';

  // Height mappings conforming strictly to recommended ranges
  const variantClasses: Record<'compact' | 'standard' | 'large' | 'hero', string> = {
    compact: 'h-8 max-h-[32px]',   // 32px (range: 28–34px)
    standard: 'h-12 max-h-[48px]', // 48px (range: 40–56px)
    large: 'h-18 max-h-[72px]',    // 72px (range: 64–84px)
    hero: 'h-24 max-h-[96px]',     // 96px (range: 90–120px)
  };

  const customStyle = size ? { height: `${size}px` } : undefined;

  return (
    <div className={`inline-flex items-center justify-center select-none ${className}`}>
      <img
        src={logoSrc}
        alt={alt}
        style={customStyle}
        className={`w-auto object-contain block ${size ? '' : variantClasses[variant]} ${imageClassName}`}
        loading="eager"
      />
    </div>
  );
};

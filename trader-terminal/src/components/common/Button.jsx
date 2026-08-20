import React from 'react';

/**
 * Institutional Trading Terminal Button Component
 * Supporting Primary Amber (#E3A83B), Outline, and Danger variants.
 */
export default function Button({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled = false,
  type = 'button',
  ...props
}) {
  const baseStyle = "inline-flex items-center justify-center font-medium rounded transition-all focus:outline-none focus:ring-2 focus:ring-amber-500/50 disabled:opacity-50 disabled:cursor-not-allowed";

  const variantStyles = {
    primary: "bg-[#E3A83B] hover:bg-[#F2BA4E] text-[#07090E] font-bold shadow-sm active:translate-y-[0.5px]",
    secondary: "bg-[#1E2D3D] hover:bg-[#283C50] text-[#F1F5F9] border border-[#23354A]",
    outline: "bg-transparent hover:bg-white/5 text-[#F1F5F9] border border-[#23354A]",
    danger: "bg-[#C24A3E] hover:bg-[#D4594C] text-white font-bold shadow-sm",
    success: "bg-[#4C9A6A] hover:bg-[#5AA878] text-white font-bold shadow-sm"
  };

  const sizeStyles = {
    sm: "px-2.5 py-1 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base font-semibold"
  };

  const combinedClass = `${baseStyle} ${variantStyles[variant] || variantStyles.primary} ${sizeStyles[size] || sizeStyles.md} ${className}`;

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={combinedClass}
      {...props}
    >
      {children}
    </button>
  );
}

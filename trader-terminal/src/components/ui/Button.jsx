import React from 'react';

export function Button({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive'
  size = 'md', // 'sm' | 'md' | 'lg'
  className = '',
  disabled = false,
  ...props
}) {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] disabled:pointer-events-none disabled:opacity-50 cursor-pointer rounded-md';

  const variantStyles = {
    primary: 'bg-[var(--primary)] text-white hover:bg-opacity-90 shadow',
    secondary: 'bg-[var(--surface-light)] text-[var(--text-dark)] hover:bg-opacity-80 border border-[var(--border-dark)]',
    outline: 'border border-[var(--primary)] text-[var(--primary)] hover:bg-[var(--primary-light)]',
    ghost: 'hover:bg-[var(--surface-light)] text-[var(--text-dark)]',
    destructive: 'bg-[var(--danger)] text-white hover:bg-opacity-90 shadow'
  };

  const sizeStyles = {
    sm: 'h-8 px-3 text-xs',
    md: 'h-10 px-4 py-2 text-sm',
    lg: 'h-12 px-6 text-base'
  };

  const computedClassName = `${baseStyles} ${variantStyles[variant] || variantStyles.primary} ${sizeStyles[size] || sizeStyles.md} ${className}`.trim();

  return (
    <button className={computedClassName} disabled={disabled} {...props}>
      {children}
    </button>
  );
}

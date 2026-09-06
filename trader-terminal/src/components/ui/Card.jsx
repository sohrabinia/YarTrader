import React from 'react';

export function Card({ className = '', children, ...props }) {
  return (
    <div
      className={`rounded-xl border border-[var(--border-dark)] bg-[var(--surface-dark)] text-[var(--text-dark)] shadow-sm p-6 ${className}`.trim()}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className = '', children, ...props }) {
  return (
    <div className={`flex flex-col space-y-1.5 pb-4 ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ className = '', children, ...props }) {
  return (
    <h3 className={`text-lg font-semibold leading-none tracking-tight text-[var(--primary)] ${className}`.trim()} {...props}>
      {children}
    </h3>
  );
}

export function CardDescription({ className = '', children, ...props }) {
  return (
    <p className={`text-sm text-[var(--text-muted)] ${className}`.trim()} {...props}>
      {children}
    </p>
  );
}

export function CardContent({ className = '', children, ...props }) {
  return (
    <div className={`pt-0 ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ className = '', children, ...props }) {
  return (
    <div className={`flex items-center pt-4 border-t border-[var(--border-dark)] ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

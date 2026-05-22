import React from 'react';

export const LoadingSkeleton = ({ 
  className = '', 
  variant = 'default',
  width,
  height,
  count = 1 
}) => {
  const baseClasses = 'animate-pulse bg-gray-700 rounded';
  
  const getVariantClasses = () => {
    switch (variant) {
      case 'circle':
        return 'rounded-full';
      case 'rectangle':
        return 'rounded';
      case 'text':
        return 'h-4 rounded';
      case 'title':
        return 'h-6 rounded';
      case 'avatar':
        return 'w-10 h-10 rounded-full';
      default:
        return 'rounded';
    }
  };
  
  const style = {
    width: width || '100%',
    height: height || (variant === 'text' ? '1rem' : variant === 'title' ? '1.5rem' : '2rem')
  };
  
  const skeletons = Array.from({ length: count }, (_, i) => (
    <div
      key={i}
      className={`${baseClasses} ${getVariantClasses()} ${className}`}
      style={style}
      aria-hidden="true"
    />
  ));
  
  return <>{skeletons}</>;
};

export const CardSkeleton = () => (
  <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
    <div className="flex items-center gap-4 mb-4">
      <LoadingSkeleton variant="circle" width={40} height={40} />
      <div className="flex-1">
        <LoadingSkeleton variant="title" width="60%" />
        <LoadingSkeleton variant="text" width="80%" className="mt-2" />
      </div>
    </div>
    <LoadingSkeleton variant="text" count={3} />
  </div>
);

export const ListSkeleton = ({ count = 3 }) => (
  <div className="space-y-3">
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
        <LoadingSkeleton variant="circle" width={32} height={32} />
        <div className="flex-1">
          <LoadingSkeleton variant="text" width="70%" />
          <LoadingSkeleton variant="text" width="50%" className="mt-1" />
        </div>
      </div>
    ))}
  </div>
);

export const TableSkeleton = ({ rows = 5, columns = 4 }) => (
  <div className="w-full">
    {/* Header */}
    <div className="flex gap-4 mb-3 pb-3 border-b border-gray-700">
      {Array.from({ length: columns }).map((_, i) => (
        <LoadingSkeleton key={i} variant="text" width="20%" />
      ))}
    </div>
    {/* Rows */}
    {Array.from({ length: rows }).map((_, rowIndex) => (
      <div key={rowIndex} className="flex gap-4 py-3 border-b border-gray-700/50">
        {Array.from({ length: columns }).map((_, colIndex) => (
          <LoadingSkeleton key={colIndex} variant="text" width="20%" />
        ))}
      </div>
    ))}
  </div>
);

export const SessionSkeleton = () => (
  <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
    <div className="flex justify-between items-start mb-3">
      <div className="flex-1">
        <LoadingSkeleton variant="title" width="40%" />
        <LoadingSkeleton variant="text" width="80%" className="mt-2" />
        <div className="flex items-center space-x-3 mt-2">
          <LoadingSkeleton variant="text" width="30%" />
          <LoadingSkeleton variant="text" width="25%" />
          <LoadingSkeleton variant="text" width="20%" />
        </div>
      </div>
      <LoadingSkeleton variant="rectangle" width={80} height={24} />
    </div>
    <div className="mt-3 pt-3 border-t border-gray-700">
      <div className="flex justify-between mb-1">
        <LoadingSkeleton variant="text" width="30%" />
        <LoadingSkeleton variant="text" width="15%" />
      </div>
      <LoadingSkeleton variant="rectangle" width="100%" height={8} />
    </div>
  </div>
);

export const DharmaTaleSkeleton = () => (
  <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
    <div className="flex items-center justify-between mb-4">
      <LoadingSkeleton variant="title" width="30%" />
      <div className="flex gap-2">
        <LoadingSkeleton variant="rectangle" width={60} height={28} />
        <LoadingSkeleton variant="rectangle" width={60} height={28} />
        <LoadingSkeleton variant="rectangle" width={60} height={28} />
      </div>
    </div>
    <LoadingSkeleton variant="text" count={4} />
    <div className="mt-4 flex justify-end">
      <LoadingSkeleton variant="rectangle" width={120} height={36} />
    </div>
  </div>
);

export default LoadingSkeleton;

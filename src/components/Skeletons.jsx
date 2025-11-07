export const SkeletonCard = ({ delay = 0 }) => (
  <div 
    className="glass-card rounded-xl p-6 animate-skeleton hover-lift"
    style={{ animationDelay: `${delay}ms` }}
  >
    <div className="flex items-center justify-between mb-4">
      <div className="h-4 rounded w-1/3 skeleton-gradient"></div>
      <div className="h-8 w-8 rounded-lg skeleton-gradient"></div>
    </div>
    <div className="h-8 rounded w-1/2 skeleton-gradient"></div>
  </div>
);

export const SkeletonTableRow = ({ delay = 0 }) => (
  <tr 
    className="border-b border-gray-700 animate-skeleton"
    style={{ animationDelay: `${delay}ms` }}
  >
    <td className="p-4">
      <div className="h-4 rounded w-3/4 skeleton-gradient"></div>
    </td>
    <td className="p-4">
      <div className="h-4 rounded w-1/2 skeleton-gradient"></div>
    </td>
    <td className="p-4">
      <div className="h-4 rounded w-1/4 skeleton-gradient"></div>
    </td>
    <td className="p-4">
      <div className="h-6 rounded w-20 skeleton-gradient"></div>
    </td>
    <td className="p-4">
      <div className="h-8 rounded w-16 skeleton-gradient"></div>
    </td>
  </tr>
);

export const SkeletonUpload = () => (
  <div className="border-2 border-dashed border-gray-600 rounded-xl p-12 text-center animate-skeleton hover-lift">
    <div className="h-16 w-16 rounded-full skeleton-gradient mx-auto mb-6"></div>
    <div className="space-y-3">
      <div className="h-6 rounded w-1/2 skeleton-gradient mx-auto"></div>
      <div className="h-4 rounded w-3/4 skeleton-gradient mx-auto"></div>
      <div className="h-3 rounded w-1/3 skeleton-gradient mx-auto"></div>
    </div>
  </div>
);

export const SkeletonStats = () => (
  <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
    <SkeletonCard delay={0} />
    <SkeletonCard delay={100} />
    <SkeletonCard delay={200} />
    <SkeletonCard delay={300} />
  </div>
);
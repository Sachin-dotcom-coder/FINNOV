import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { AlertTriangle, X, CheckCircle2 } from 'lucide-react';

const AnomalyCard = ({ anomaly, onResolve }) => {
  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high':
        return 'text-destructive bg-destructive/10 border-destructive/20';
      case 'medium':
        return 'text-warning bg-warning/10 border-warning/20';
      case 'low':
        return 'text-muted-foreground bg-muted border-border';
      default:
        return 'text-muted-foreground bg-muted border-border';
    }
  };

  const getPriorityIcon = (priority) => {
    return <AlertTriangle className="h-4 w-4" />;
  };

  return (
    <div className="border rounded-lg p-4 animate-fade-in-up glass-panel">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${getPriorityColor(anomaly.priority)}`}>
            {getPriorityIcon(anomaly.priority)}
          </div>
          <div>
            <h4 className="font-semibold">{anomaly.description}</h4>
            <Badge variant={anomaly.priority} className="mt-1">
              {anomaly.priority} priority
            </Badge>
          </div>
        </div>
      </div>

      <p className="text-muted-foreground text-sm mb-4">
        {anomaly.details}
      </p>

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onResolve(anomaly.id, 'reject')}
          className="gap-2 flex-1"
        >
          <X className="h-4 w-4" />
          False Detection
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => onResolve(anomaly.id, 'accept')}
          className="gap-2 flex-1"
        >
          <CheckCircle2 className="h-4 w-4" />
          Accept
        </Button>
      </div>
    </div>
  );
};

export default AnomalyCard;
import RecommendationCard from "./RecommendationCard";
import EmptyState from "../ui/EmptyState";

export default function RecommendationList({ recommendations }) {
  if (!recommendations || recommendations.length === 0) {
    return <EmptyState message="No recommendations generated for the current state." />;
  }
  return (
    <div className="space-y-3">
      {recommendations.map((rec) => (
        <RecommendationCard key={rec.recommendation_id} rec={rec} />
      ))}
    </div>
  );
}

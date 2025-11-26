#!/usr/bin/env python3
"""
Comprehensive IR Sensor Test Runner
Runs all test scenarios and generates a detailed report
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from ir_sensor_simulation import IRSensorTestSimulator

# Configure logging for test runner
logging.basicConfig(
    level=logging.WARNING,  # Reduce log noise
    format='%(levelname)s - %(message)s'
)

class ComprehensiveTestRunner:
    """Runs comprehensive tests and generates reports"""
    
    def __init__(self):
        self.simulator = IRSensorTestSimulator()
        self.results = {
            "test_metadata": {
                "start_time": datetime.now().isoformat(),
                "test_scenarios": [],
                "overall_accuracy": 0,
                "total_steps": 0,
                "correct_steps": 0
            },
            "scenario_results": {},
            "recommendations": []
        }
    
    async def run_comprehensive_test(self):
        """Run all test scenarios and generate comprehensive report"""
        print("🔬 Comprehensive IR Sensor Test Suite")
        print("=" * 60)
        
        # Initialize simulator
        if not await self.simulator.initialize():
            print("❌ Failed to initialize simulator")
            return
        
        try:
            # Get all scenarios
            scenarios = list(self.simulator.test_data["test_scenarios"].keys())
            self.results["test_metadata"]["test_scenarios"] = scenarios
            
            print(f"🧪 Running {len(scenarios)} test scenarios...")
            print("-" * 60)
            
            # Run each scenario
            for i, scenario_name in enumerate(scenarios):
                print(f"\\n[{i+1}/{len(scenarios)}] Testing: {scenario_name}")
                
                scenario_result = await self.run_single_scenario(scenario_name)
                self.results["scenario_results"][scenario_name] = scenario_result
                
                # Print brief result
                accuracy = scenario_result["accuracy"]
                status = "✅ PASS" if accuracy >= 70 else "⚠️ NEEDS IMPROVEMENT" if accuracy >= 40 else "❌ FAIL"
                print(f"    Result: {status} ({accuracy:.1f}% accuracy)")
            
            # Calculate overall results
            self.calculate_overall_results()
            
            # Generate recommendations
            self.generate_recommendations()
            
            # Save and display results
            self.save_results()
            self.display_comprehensive_report()
            
        finally:
            await self.simulator.cleanup()
    
    async def run_single_scenario(self, scenario_name):
        """Run a single scenario and collect detailed results"""
        # Load scenario
        self.simulator.load_scenario(scenario_name)
        scenario_data = self.simulator.current_scenario
        
        # Run scenario silently
        start_time = asyncio.get_event_loop().time()
        scenario_duration = scenario_data["duration"]
        
        step_results = []
        
        while (asyncio.get_event_loop().time() - start_time) < scenario_duration:
            # Get current sensor data
            current_sensor_data = self.simulator.get_current_sensor_data()
            
            # Analyze sensor data
            analyzed_action = self.simulator.analyze_sensor_data(current_sensor_data)
            
            # Record result
            expected_action = current_sensor_data.get("action", "unknown")
            is_correct = analyzed_action == expected_action
            
            step_results.append({
                "timestamp": asyncio.get_event_loop().time() - start_time,
                "sensor_data": current_sensor_data,
                "expected_action": expected_action,
                "analyzed_action": analyzed_action,
                "correct": is_correct
            })
            
            await asyncio.sleep(0.05)  # Fast simulation
        
        # Calculate scenario statistics
        total_steps = len(step_results)
        correct_steps = sum(1 for step in step_results if step["correct"])
        accuracy = (correct_steps / total_steps * 100) if total_steps > 0 else 0
        
        # Analyze action distribution
        action_distribution = {}
        error_patterns = {}
        
        for step in step_results:
            expected = step["expected_action"]
            analyzed = step["analyzed_action"]
            
            # Count actions
            action_distribution[analyzed] = action_distribution.get(analyzed, 0) + 1
            
            # Count error patterns
            if not step["correct"]:
                error_key = f"{expected} -> {analyzed}"
                error_patterns[error_key] = error_patterns.get(error_key, 0) + 1
        
        return {
            "scenario_name": scenario_name,
            "description": scenario_data["description"],
            "total_steps": total_steps,
            "correct_steps": correct_steps,
            "accuracy": accuracy,
            "action_distribution": action_distribution,
            "error_patterns": error_patterns,
            "step_details": step_results[-10:]  # Keep last 10 steps for debugging
        }
    
    def calculate_overall_results(self):
        """Calculate overall test results"""
        total_steps = 0
        correct_steps = 0
        
        for scenario_result in self.results["scenario_results"].values():
            total_steps += scenario_result["total_steps"]
            correct_steps += scenario_result["correct_steps"]
        
        overall_accuracy = (correct_steps / total_steps * 100) if total_steps > 0 else 0
        
        self.results["test_metadata"]["total_steps"] = total_steps
        self.results["test_metadata"]["correct_steps"] = correct_steps
        self.results["test_metadata"]["overall_accuracy"] = overall_accuracy
        self.results["test_metadata"]["end_time"] = datetime.now().isoformat()
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check overall accuracy
        overall_accuracy = self.results["test_metadata"]["overall_accuracy"]
        
        if overall_accuracy < 50:
            recommendations.append({
                "priority": "HIGH",
                "category": "Algorithm",
                "issue": "Low overall accuracy",
                "description": f"Overall accuracy of {overall_accuracy:.1f}% is below acceptable threshold",
                "suggestion": "Review and refine sensor analysis algorithm logic"
            })
        
        # Analyze per-scenario performance
        for scenario_name, result in self.results["scenario_results"].items():
            accuracy = result["accuracy"]
            
            if accuracy < 30:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Scenario Specific",
                    "issue": f"Poor performance in {scenario_name}",
                    "description": f"Accuracy of {accuracy:.1f}% in {scenario_name} scenario",
                    "suggestion": f"Review sensor thresholds and logic for {scenario_name} conditions"
                })
            
            # Check for common error patterns
            error_patterns = result["error_patterns"]
            for error_pattern, count in error_patterns.items():
                if count >= result["total_steps"] * 0.3:  # 30% or more errors of same type
                    recommendations.append({
                        "priority": "MEDIUM",
                        "category": "Error Pattern",
                        "issue": f"Frequent misclassification: {error_pattern}",
                        "description": f"Pattern '{error_pattern}' occurred {count} times in {scenario_name}",
                        "suggestion": "Adjust decision thresholds for this specific case"
                    })
        
        # Check for missing actions
        all_actions = set()
        analyzed_actions = set()
        
        for result in self.results["scenario_results"].values():
            for step in result["step_details"]:
                all_actions.add(step["expected_action"])
                analyzed_actions.add(step["analyzed_action"])
        
        missing_actions = all_actions - analyzed_actions
        if missing_actions:
            recommendations.append({
                "priority": "MEDIUM", 
                "category": "Coverage",
                "issue": "Missing action implementations",
                "description": f"Actions never generated: {', '.join(missing_actions)}",
                "suggestion": "Implement logic to handle these specific actions"
            })
        
        self.results["recommendations"] = recommendations
    
    def save_results(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\\n💾 Detailed results saved to: {filename}")
    
    def display_comprehensive_report(self):
        """Display comprehensive test report"""
        print("\\n" + "=" * 80)
        print("🔬 COMPREHENSIVE IR SENSOR TEST REPORT")
        print("=" * 80)
        
        # Overall summary
        meta = self.results["test_metadata"]
        print(f"\\n📊 Overall Summary:")
        print(f"   Test Date: {meta['start_time'][:19]}")
        print(f"   Scenarios Tested: {len(meta['test_scenarios'])}")
        print(f"   Total Test Steps: {meta['total_steps']}")
        print(f"   Correct Classifications: {meta['correct_steps']}")
        print(f"   Overall Accuracy: {meta['overall_accuracy']:.1f}%")
        
        # Overall rating
        accuracy = meta["overall_accuracy"]
        if accuracy >= 80:
            rating = "🟢 EXCELLENT"
        elif accuracy >= 60:
            rating = "🟡 GOOD"
        elif accuracy >= 40:
            rating = "🟠 NEEDS IMPROVEMENT"
        else:
            rating = "🔴 POOR"
        
        print(f"   Overall Rating: {rating}")
        
        # Per-scenario results
        print(f"\\n📋 Scenario Performance:")
        print(f"   {'Scenario':<25} {'Accuracy':<10} {'Steps':<8} {'Status'}")
        print(f"   {'-'*25} {'-'*10} {'-'*8} {'-'*20}")
        
        for scenario_name, result in self.results["scenario_results"].items():
            accuracy = result["accuracy"]
            steps = result["total_steps"]
            
            if accuracy >= 70:
                status = "✅ PASS"
            elif accuracy >= 40:
                status = "⚠️ REVIEW"
            else:
                status = "❌ FAIL"
            
            print(f"   {scenario_name:<25} {accuracy:>7.1f}% {steps:>6d}    {status}")
        
        # Recommendations
        recommendations = self.results["recommendations"]
        if recommendations:
            print(f"\\n🔧 Recommendations ({len(recommendations)}):")
            
            # Group by priority
            high_priority = [r for r in recommendations if r["priority"] == "HIGH"]
            medium_priority = [r for r in recommendations if r["priority"] == "MEDIUM"]
            
            if high_priority:
                print(f"\\n   🚨 HIGH PRIORITY:")
                for i, rec in enumerate(high_priority, 1):
                    print(f"      {i}. {rec['issue']}")
                    print(f"         {rec['description']}")
                    print(f"         💡 {rec['suggestion']}")
                    print()
            
            if medium_priority:
                print(f"   ⚠️ MEDIUM PRIORITY:")
                for i, rec in enumerate(medium_priority, 1):
                    print(f"      {i}. {rec['issue']}")
                    print(f"         {rec['description']}")
                    print(f"         💡 {rec['suggestion']}")
                    print()
        else:
            print(f"\\n🎉 No major issues found!")
        
        # Action distribution summary
        print(f"\\n📈 Common Actions Generated:")
        all_actions = {}
        for result in self.results["scenario_results"].values():
            for action, count in result["action_distribution"].items():
                all_actions[action] = all_actions.get(action, 0) + count
        
        sorted_actions = sorted(all_actions.items(), key=lambda x: x[1], reverse=True)
        for action, count in sorted_actions[:5]:  # Top 5
            percentage = (count / meta["total_steps"]) * 100
            print(f"   {action:<25} {count:>6d} times ({percentage:.1f}%)")
        
        print("\\n" + "=" * 80)


async def main():
    """Main function for comprehensive testing"""
    print("🤖 Medi-Runner IR Sensor Comprehensive Test Suite")
    print("This will test all scenarios and generate a detailed report.")
    print()
    
    # Confirm before running
    response = input("Do you want to run the comprehensive test? (y/n): ").strip().lower()
    if response != 'y':
        print("👋 Test cancelled")
        return
    
    # Run comprehensive test
    test_runner = ComprehensiveTestRunner()
    await test_runner.run_comprehensive_test()
    
    print("\\n🎉 Comprehensive testing complete!")
    print("\\nNext steps:")
    print("1. Review the detailed JSON results file")
    print("2. Implement recommended algorithm improvements")
    print("3. Re-run tests to validate improvements")
    print("4. Test with real hardware when available")


if __name__ == "__main__":
    asyncio.run(main())
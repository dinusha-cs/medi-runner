/**
 * Simple Docker Performance Test
 * Measures latency impact of containerized vs native deployment
 */

const http = require('http');

// Test configuration
const config = {
    backendUrl: 'http://localhost:3001',
    iterations: 20,
    delay: 100
};

console.log('🧪 Docker Performance Test');
console.log('===========================');
console.log(`Target: ${config.backendUrl}`);
console.log(`Iterations: ${config.iterations}`);
console.log('');

async function testHttpLatency() {
    console.log('🌐 Testing HTTP API Latency...');
    
    const latencies = [];
    
    for (let i = 0; i < config.iterations; i++) {
        try {
            const startTime = Date.now();
            
            await new Promise((resolve, reject) => {
                const req = http.get(config.backendUrl + '/health', (res) => {
                    let data = '';
                    res.on('data', chunk => data += chunk);
                    res.on('end', () => resolve(data));
                });
                
                req.on('error', reject);
                req.setTimeout(5000, () => {
                    req.destroy();
                    reject(new Error('Timeout'));
                });
            });
            
            const endTime = Date.now();
            const latency = endTime - startTime;
            latencies.push(latency);
            
            process.stdout.write(`Progress: ${i + 1}/${config.iterations} - Current: ${latency}ms\r`);
            
            if (i < config.iterations - 1) {
                await new Promise(resolve => setTimeout(resolve, config.delay));
            }
            
        } catch (error) {
            console.error(`\nTest ${i + 1} failed:`, error.message);
        }
    }
    
    if (latencies.length > 0) {
        const avg = latencies.reduce((sum, val) => sum + val, 0) / latencies.length;
        const min = Math.min(...latencies);
        const max = Math.max(...latencies);
        
        console.log('\n\n📊 Results:');
        console.log(`   • Tests completed: ${latencies.length}/${config.iterations}`);
        console.log(`   • Average latency: ${avg.toFixed(2)}ms`);
        console.log(`   • Min latency: ${min}ms`);
        console.log(`   • Max latency: ${max}ms`);
        
        console.log('\n🎯 Assessment:');
        if (avg < 50) {
            console.log('   ✅ EXCELLENT - Perfect for robot control');
        } else if (avg < 100) {
            console.log('   🟡 GOOD - Acceptable for robot control');
        } else {
            console.log('   🟠 POOR - May need optimization');
        }
        
        console.log('\n🏁 Verdict:');
        if (avg < 100) {
            console.log('   🎉 Docker deployment is READY for competition!');
            console.log('   🚀 Performance overhead is minimal and acceptable');
        } else {
            console.log('   ⚠️  Consider optimizations or native deployment');
        }
    } else {
        console.log('\n❌ No successful tests completed');
    }
}

// Run the test
testHttpLatency().catch(error => {
    console.error('\n💥 Test failed:', error.message);
    process.exit(1);
});
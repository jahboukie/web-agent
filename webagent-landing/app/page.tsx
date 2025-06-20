'use client'

import { useState } from 'react'
import { Eye, Brain, Shield, Play, Mail, CheckCircle, ArrowRight, Sparkles, Lock, Zap } from 'lucide-react'

export default function LandingPage() {
  const [email, setEmail] = useState('')
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    setIsLoading(true)
    
    // Simulate API call - replace with actual email service integration
    setTimeout(() => {
      setIsSubmitted(true)
      setIsLoading(false)
      setEmail('')
    }, 1000)
  }

  return (
    <main className="min-h-screen bg-white">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-gray-50 via-white to-blue-50">
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-blue-600/5 via-transparent to-purple-600/5"></div>
        
        <div className="relative container-custom section-padding">
          <div className="text-center max-w-5xl mx-auto">
            {/* Badge */}
            <div className="inline-flex items-center space-x-2 bg-blue-100 text-blue-800 px-4 py-2 rounded-full text-sm font-medium mb-8 animate-fade-in">
              <Sparkles className="h-4 w-4" />
              <span>Private Beta Now Available</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold mb-8 animate-slide-up">
              <span className="block text-gray-900 mb-2">The Agentic Web</span>
              <span className="block gradient-text">is Here.</span>
            </h1>

            {/* Sub-headline */}
            <p className="text-xl md:text-2xl lg:text-3xl text-gray-600 mb-12 max-w-4xl mx-auto leading-relaxed animate-slide-up" style={{ animationDelay: '0.2s' }}>
              WebAgent is a fully autonomous AI agent that can{' '}
              <span className="text-blue-600 font-semibold">understand any website</span>,{' '}
              <span className="text-purple-600 font-semibold">create a plan</span>, and{' '}
              <span className="text-green-600 font-semibold">execute complex tasks</span>{' '}
              on your behalf.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center animate-slide-up" style={{ animationDelay: '0.4s' }}>
              <a href="#beta-signup" className="btn-primary inline-flex items-center space-x-2">
                <span>Request Private Beta Access</span>
                <ArrowRight className="h-5 w-5" />
              </a>
              <a href="#demo" className="btn-secondary inline-flex items-center space-x-2">
                <Play className="h-5 w-5" />
                <span>See it in Action</span>
              </a>
            </div>

            {/* Trust Indicators */}
            <div className="mt-16 flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-8 text-sm text-gray-500 animate-fade-in" style={{ animationDelay: '0.6s' }}>
              <div className="flex items-center space-x-2">
                <Shield className="h-4 w-4 text-green-500" />
                <span>Enterprise-Grade Security</span>
              </div>
              <div className="flex items-center space-x-2">
                <Lock className="h-4 w-4 text-blue-500" />
                <span>Zero-Knowledge Architecture</span>
              </div>
              <div className="flex items-center space-x-2">
                <Zap className="h-4 w-4 text-purple-500" />
                <span>Fully Autonomous</span>
              </div>
            </div>
          </div>
        </div>

        {/* Floating Elements */}
        <div className="absolute top-20 left-10 w-20 h-20 bg-blue-200 rounded-full opacity-20 animate-float"></div>
        <div className="absolute top-40 right-20 w-16 h-16 bg-purple-200 rounded-full opacity-20 animate-float" style={{ animationDelay: '2s' }}></div>
        <div className="absolute bottom-20 left-20 w-12 h-12 bg-green-200 rounded-full opacity-20 animate-float" style={{ animationDelay: '4s' }}></div>
      </section>

      {/* Demo Placeholder Section */}
      <section id="demo" className="section-padding bg-gray-50">
        <div className="container-custom">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              See it in Action
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Watch WebAgent understand, plan, and execute complex web tasks in real-time. 
              This is the future of web automation.
            </p>
          </div>

          {/* Demo Video Placeholder */}
          <div className="max-w-5xl mx-auto">
            <div className="relative bg-gray-900 rounded-2xl overflow-hidden shadow-2xl">
              <div className="aspect-video flex items-center justify-center bg-gradient-to-br from-gray-800 to-gray-900">
                <div className="text-center">
                  <div className="w-24 h-24 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Play className="h-12 w-12 text-white ml-1" />
                  </div>
                  <h3 className="text-2xl font-semibold text-white mb-2">2-Minute Miracle</h3>
                  <p className="text-gray-300 text-lg">Demo video coming soon</p>
                </div>
              </div>
              
              {/* Video Controls Mockup */}
              <div className="absolute bottom-0 left-0 right-0 bg-black/50 p-4">
                <div className="flex items-center space-x-4">
                  <button className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                    <Play className="h-5 w-5 text-white ml-0.5" />
                  </button>
                  <div className="flex-1 bg-white/20 h-1 rounded-full">
                    <div className="w-1/3 bg-blue-500 h-1 rounded-full"></div>
                  </div>
                  <span className="text-white text-sm">0:45 / 2:00</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Features Section */}
      <section className="section-padding bg-white">
        <div className="container-custom">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              Three Revolutionary Capabilities
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              WebAgent combines advanced AI with secure execution to deliver unprecedented web automation capabilities.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-12 lg:gap-16">
            {/* EYES - Semantic Understanding */}
            <div className="text-center group card-hover">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-8 group-hover:scale-110 transition-transform duration-300">
                <Eye className="h-10 w-10 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">EYES</h3>
              <h4 className="text-lg font-semibold text-blue-600 mb-4">Semantic Understanding</h4>
              <p className="text-gray-600 leading-relaxed">
                Goes beyond simple scraping to understand the content and function of any webpage. 
                WebAgent sees the web like a human does.
              </p>
            </div>

            {/* BRAIN - AI Planning */}
            <div className="text-center group card-hover">
              <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-8 group-hover:scale-110 transition-transform duration-300">
                <Brain className="h-10 w-10 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">BRAIN</h3>
              <h4 className="text-lg font-semibold text-purple-600 mb-4">AI Planning</h4>
              <p className="text-gray-600 leading-relaxed">
                Dynamically generates a strategic, step-by-step plan to achieve any high-level goal. 
                Intelligence that adapts to any scenario.
              </p>
            </div>

            {/* HANDS - Secure Execution */}
            <div className="text-center group card-hover">
              <div className="w-20 h-20 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center mx-auto mb-8 group-hover:scale-110 transition-transform duration-300">
                <Shield className="h-10 w-10 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">HANDS</h3>
              <h4 className="text-lg font-semibold text-green-600 mb-4">Secure Execution</h4>
              <p className="text-gray-600 leading-relaxed">
                Executes plans in a hardened browser, with every critical action approved by you. 
                Power with complete control and security.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Security Promise Section */}
      <section className="section-padding bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 text-white">
        <div className="container-custom">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center space-x-2 bg-white/10 backdrop-blur-sm px-4 py-2 rounded-full text-sm font-medium mb-8">
              <Shield className="h-4 w-4" />
              <span>Security First</span>
            </div>

            <h2 className="text-4xl md:text-5xl font-bold mb-8">
              Enterprise-Grade Security from Day One
            </h2>
            
            <p className="text-xl md:text-2xl text-gray-300 mb-12 leading-relaxed">
              Built on a <span className="text-blue-400 font-semibold">Zero-Knowledge</span>, 
              <span className="text-purple-400 font-semibold"> Zero Trust</span> architecture 
              to ensure your data and credentials are kept 
              <span className="text-green-400 font-semibold"> mathematically secure</span>.
            </p>

            <div className="grid md:grid-cols-3 gap-8 text-center">
              <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6">
                <Lock className="h-8 w-8 text-blue-400 mx-auto mb-4" />
                <h3 className="font-semibold mb-2">Zero-Knowledge</h3>
                <p className="text-gray-400 text-sm">We never see your data or credentials</p>
              </div>
              <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6">
                <Shield className="h-8 w-8 text-purple-400 mx-auto mb-4" />
                <h3 className="font-semibold mb-2">Zero Trust</h3>
                <p className="text-gray-400 text-sm">Every action requires explicit approval</p>
              </div>
              <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6">
                <CheckCircle className="h-8 w-8 text-green-400 mx-auto mb-4" />
                <h3 className="font-semibold mb-2">Enterprise Ready</h3>
                <p className="text-gray-400 text-sm">SOC2 compliant from day one</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Beta Signup CTA Section */}
      <section id="beta-signup" className="section-padding bg-white">
        <div className="container-custom">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              Ready to Experience the Future?
            </h2>
            <p className="text-xl text-gray-600 mb-12">
              Join the private beta and be among the first to harness the power of truly autonomous web agents.
            </p>

            {!isSubmitted ? (
              <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
                <div className="flex flex-col sm:flex-row gap-4">
                  <div className="flex-1">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="Enter your email address"
                      className="w-full px-6 py-4 text-lg border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="btn-primary whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? (
                      <span className="flex items-center space-x-2">
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Submitting...</span>
                      </span>
                    ) : (
                      <span className="flex items-center space-x-2">
                        <span>Request Private Beta Access</span>
                        <ArrowRight className="h-5 w-5" />
                      </span>
                    )}
                  </button>
                </div>
                <p className="text-sm text-gray-500 mt-4">
                  No spam, ever. Unsubscribe at any time.
                </p>
              </form>
            ) : (
              <div className="max-w-md mx-auto bg-green-50 border border-green-200 rounded-lg p-8">
                <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-green-800 mb-2">You're on the list!</h3>
                <p className="text-green-700">
                  We'll be in touch soon with your private beta access. 
                  Get ready to experience the future of web automation.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="container-custom">
          <div className="text-center">
            <div className="flex items-center justify-center space-x-2 mb-4">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">W</span>
              </div>
              <span className="text-xl font-bold">WebAgent</span>
            </div>
            <p className="text-gray-400 mb-4">The Agentic Web is Here.</p>
            <p className="text-gray-500 text-sm">
              © 2025 WebAgent. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </main>
  )
}

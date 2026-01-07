import React from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  ZAxis
} from 'recharts'
import { QueryResponse } from '../types'
import { BarChart3, TrendingUp, PieChart as PieChartIcon, Table, Activity, GitBranch } from 'lucide-react'
import type { TooltipProps } from 'recharts'

interface ChartDisplayProps {
  queryResult: QueryResponse
}

export const ChartDisplay: React.FC<ChartDisplayProps> = ({ queryResult }) => {
  const { data, chart_type } = queryResult

  if (!data || data.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
        <Table className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-gray-500">표시할 데이터가 없습니다.</p>
      </div>
    )
  }

  // 색상 팔레트
  const colors = [
    '#3B82F6', // blue-500
    '#EF4444', // red-500
    '#10B981', // emerald-500
    '#F59E0B', // amber-500
    '#8B5CF6', // violet-500
    '#EC4899', // pink-500
    '#06B6D4', // cyan-500
    '#84CC16'  // lime-500
  ]

  // 커스텀 툴팁
  const CustomTooltip = ({
    active,
    payload,
    label,
  }: TooltipProps<number, string>) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <p className="font-medium text-gray-900 mb-1">{label}</p>
          {payload.map((entry, index) => {
            if (!entry) return null
            const value = entry.value
            return (
              <p key={index} className="text-sm" style={{ color: entry.color }}>
                {entry.name}: {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </p>
            )
          })}
        </div>
      )
    }
    return null
  }

  const renderChart = () => {
    // 데이터가 있는지 확인하고 첫 번째 행의 키를 가져옴
    const firstRowKeys = data.length > 0 ? Object.keys(data[0]) : []

    switch (chart_type) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis 
                dataKey={Object.keys(data[0])[0]} 
                tick={{ fontSize: 12 }}
                stroke="#6b7280"
              />
              <YAxis tick={{ fontSize: 12 }} stroke="#6b7280" />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              {Object.keys(data[0]).slice(1).map((key, index) => (
                <Bar 
                  key={key} 
                  dataKey={key} 
                  fill={colors[index % colors.length]}
                  radius={[2, 2, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis 
                dataKey={Object.keys(data[0])[0]} 
                tick={{ fontSize: 12 }}
                stroke="#6b7280"
              />
              <YAxis tick={{ fontSize: 12 }} stroke="#6b7280" />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              {Object.keys(data[0]).slice(1).map((key, index) => (
                <Line 
                  key={key} 
                  type="monotone" 
                  dataKey={key} 
                  stroke={colors[index % colors.length]}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )

      case 'pie':
        {
          const pieData = data.map((item, index) => ({
            name: item[Object.keys(item)[0]],
            value: item[Object.keys(item)[1]],
            fill: colors[index % colors.length]
          }))

          return (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          )
        }

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey={firstRowKeys[0]}
                tick={{ fontSize: 12 }}
                stroke="#6b7280"
              />
              <YAxis tick={{ fontSize: 12 }} stroke="#6b7280" />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              {firstRowKeys.slice(1).map((key, index) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={colors[index % colors.length]}
                  fill={colors[index % colors.length]}
                  fillOpacity={0.6}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'scatter':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey={firstRowKeys[0]}
                tick={{ fontSize: 12 }}
                stroke="#6b7280"
                type="number"
              />
              <YAxis
                dataKey={firstRowKeys[1]}
                tick={{ fontSize: 12 }}
                stroke="#6b7280"
                type="number"
              />
              <ZAxis range={[100, 400]} />
              <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
              <Legend />
              <Scatter
                name={firstRowKeys[1] || 'data'}
                data={data}
                fill={colors[0]}
              />
            </ScatterChart>
          </ResponsiveContainer>
        )

      default:
        // 테이블 형태로 표시
        return (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {Object.keys(data[0]).map((key) => (
                    <th
                      key={key}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.map((row, index) => (
                  <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    {Object.values(row).map((value, cellIndex) => (
                      <td key={cellIndex} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {typeof value === 'number' ? value.toLocaleString() : String(value)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
    }
  }

  const getChartIcon = () => {
    switch (chart_type) {
      case 'bar':
        return <BarChart3 className="w-4 h-4" />
      case 'line':
        return <TrendingUp className="w-4 h-4" />
      case 'pie':
        return <PieChartIcon className="w-4 h-4" />
      case 'area':
        return <Activity className="w-4 h-4" />
      case 'scatter':
        return <GitBranch className="w-4 h-4" />
      default:
        return <Table className="w-4 h-4" />
    }
  }

  const getChartTitle = () => {
    switch (chart_type) {
      case 'bar':
        return '막대 차트'
      case 'line':
        return '선 차트'
      case 'pie':
        return '파이 차트'
      case 'area':
        return '영역 차트'
      case 'scatter':
        return '산점도 차트'
      default:
        return '데이터 테이블'
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* 차트 헤더 */}
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <div className="text-gray-600">
            {getChartIcon()}
          </div>
          <h3 className="text-sm font-medium text-gray-900">{getChartTitle()}</h3>
          <span className="text-xs text-gray-500">({data.length}개 항목)</span>
        </div>
      </div>

      {/* 차트 내용 */}
      <div className="p-4">
        {renderChart()}
      </div>
    </div>
  )
}

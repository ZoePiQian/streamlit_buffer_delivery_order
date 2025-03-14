import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime

# 预定义配置
PILL_OPTIONS = ["Xiaofeng Hou", "Becky Chen", "Yerik Yao"]
CLIENT_OPTIONS = ["客户A", "客户B", "客户C"]  # 可替换为实际客户列表
REQUIRED_COLUMNS = ['客户名称', 'CAD', '数量', '到货日期']

def initialize_session_state():
    """初始化所有session state数据"""
    for planner in PILL_OPTIONS:
        # 文件数据存储
        if f"file_{planner}" not in st.session_state:
            st.session_state[f"file_{planner}"] = pd.DataFrame(columns=REQUIRED_COLUMNS)
        # 批量输入数据
        if f"batch_{planner}" not in st.session_state:
            st.session_state[f"batch_{planner}"] = {
                'selected_client': '',
                'entries': []
            }
        # 已提交数据
        if f"submitted_{planner}" not in st.session_state:
            st.session_state[f"submitted_{planner}"] = pd.DataFrame(columns=REQUIRED_COLUMNS)

def convert_date_column(df):
    """确保日期列转换为datetime类型"""
    if '到货日期' in df.columns:
        df['到货日期'] = pd.to_datetime(df['到货日期'], errors='coerce')
    return df

def handle_file_upload(planner):
    """处理文件上传"""
    with st.container(border=True):
        st.subheader("📤 文件在这里上传")
        uploaded_file = st.file_uploader(
            f"上传{planner}的文件（CSV/Excel）",
            type=["csv", "xlsx"],
            key=f"upload_{planner}"
        )
        
        if uploaded_file:
            try:
                # 读取文件
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file, engine='openpyxl')
                
                # 转换日期列
                df = convert_date_column(df)
                
                # 验证字段
                missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
                if missing_cols:
                    st.error(f"缺少必要字段: {', '.join(missing_cols)}")
                    return
                
                # 更新session state
                st.session_state[f"file_{planner}"] = df[REQUIRED_COLUMNS]
                st.success("文件上传成功！")
                
                # 显示预览
                with st.expander("点击查看这个文件内容"):
                    st.dataframe(st.session_state[f"file_{planner}"])
                    
            except Exception as e:
                st.error(f"文件处理错误: {str(e)}")

def validate_batch(planner):
    """验证批量输入数据"""
    batch = st.session_state[f"batch_{planner}"]
    if not batch['selected_client']:
        return False, "请选择客户名称"
    
    for i, entry in enumerate(batch['entries'], 1):
        if not entry['CAD'].strip():
            return False, f"第{i}行CAD编号不能为空"
        if entry['数量'] is None or entry['数量'] < 0:
            return False, f"第{i}行数量无效（需≥0）"
        if not entry['到货日期']:
            return False, f"第{i}行到货日期未选择"
    return True, ""

def handle_batch_input(planner):
    """处理批量输入"""
    with st.container(border=True):
        st.subheader("📝 批量输入（同一客户）")
        
        # 客户选择
        client = st.selectbox(
            "选择客户名称 *",
            options=[""] + CLIENT_OPTIONS,
            key=f"client_select_{planner}"
        )
        st.session_state[f"batch_{planner}"]['selected_client'] = client
        
        # 动态输入表格
        entries = st.session_state[f"batch_{planner}"]['entries']
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown("**输入条目（可添加多个CAD）**")
        with col2:
            if st.button("➕ 添加行", key=f"add_row_{planner}"):
                entries.append({'CAD': '', '数量': None, '到货日期': datetime.today().date()})
        
        # 输入行管理
        for i in range(len(entries)):
            cols = st.columns([3, 2, 3, 1])
            with cols[0]:
                entries[i]['CAD'] = st.text_input(
                    f"CAD编号 {i+1} *",
                    value=entries[i]['CAD'],
                    key=f"cad_{i}_{planner}"
                )
            with cols[1]:
                entries[i]['数量'] = st.number_input(
                    "数量 *",
                    min_value=0,
                    value=entries[i]['数量'] or 0,
                    key=f"qty_{i}_{planner}"
                )
            with cols[2]:
                entries[i]['到货日期'] = st.date_input(
                    "到货日期 *",
                    value=entries[i]['到货日期'],
                    format="YYYY-MM-DD",
                    key=f"date_{i}_{planner}"
                )
            with cols[3]:
                if st.button("❌", key=f"del_{i}_{planner}"):
                    entries.pop(i)
                    st.rerun()
        
        # 提交按钮
        if st.button("🚀 提交全部条目", type="primary", key=f"submit_batch_{planner}"):
            valid, msg = validate_batch(planner)
            if valid:
                # 创建新数据
                new_data = [{
                    '客户名称': client,
                    'CAD': entry['CAD'],
                    '数量': entry['数量'],
                    '到货日期': entry['到货日期']
                } for entry in entries]
                
                # 合并数据
                new_df = pd.DataFrame(new_data)
                st.session_state[f"submitted_{planner}"] = pd.concat([
                    st.session_state[f"submitted_{planner}"],
                    new_df
                ], ignore_index=True)
                
                # 清空输入
                st.session_state[f"batch_{planner}"] = {
                    'selected_client': '',
                    'entries': []
                }
                st.success(f"成功提交 {len(new_data)} 条记录！")
                st.rerun()
            else:
                st.error(f"提交失败: {msg}")

        # 显示已提交数据
        if not st.session_state[f"submitted_{planner}"].empty:
            st.markdown("**已提交数据**")
            st.dataframe(
                st.session_state[f"submitted_{planner}"],
                use_container_width=True,
                hide_index=True
            )

def summary_page():
    """数据汇总页面"""
    st.title("📊 数据总览")
    st.markdown("---")
    
    # 合并所有数据
    all_data = []
    for planner in PILL_OPTIONS:
        combined = pd.concat([
            st.session_state[f"file_{planner}"],
            st.session_state[f"submitted_{planner}"]
        ], ignore_index=True)
        
        if not combined.empty:
            combined["提交人"] = planner
            all_data.append(combined)
    
    if not all_data:
        st.warning("当前没有可显示的数据")
        return
    
    total_df = pd.concat(all_data, ignore_index=True)
    
    # 显示数据
    st.dataframe(
        total_df,
        use_container_width=True,
        column_order=["提交人"] + REQUIRED_COLUMNS,
        hide_index=True,
        column_config={
            "到货日期": st.column_config.DateColumn(format="YYYY-MM-DD")
        }
    )
    
    # 导出功能
    st.markdown("---")
    with st.container(border=True):
        st.subheader("📥 数据导出")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            export_format = st.selectbox("导出格式", ["CSV", "Excel"])
            export_btn = st.button("生成文件", type="primary")
        
        with col2:
            export_name = st.text_input("文件名", "buffer_plan_summary")
        
        if export_btn:
            try:
                export_df = total_df.copy()
                export_df['到货日期'] = export_df['到货日期'].dt.strftime('%Y-%m-%d')
                
                if export_format == "CSV":
                    csv = export_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "下载CSV",
                        data=csv,
                        file_name=f"{export_name}.csv",
                        mime="text/csv"
                    )
                else:
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        export_df.to_excel(writer, index=False)
                    st.download_button(
                        "下载Excel",
                        data=output.getvalue(),
                        file_name=f"{export_name}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"导出失败: {str(e)}")

def main():
    """主程序"""
    st.set_page_config(
        page_title="Buffer要货管理系统",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    initialize_session_state()
    
    # 导航菜单
    st.sidebar.title("功能导航")
    page = st.sidebar.radio("页面选择", ["数据录入", "数据总览"])
    
    if page == "数据录入":
        st.title("📝 数据录入页面")
        st.markdown("---")
        planner = st.radio(
            "选择您的账号",
            PILL_OPTIONS,
            index=0,
            horizontal=True,
            key="planner_select"
        )
        st.markdown("---")
        handle_file_upload(planner)
        handle_batch_input(planner)
    else:
        summary_page()

if __name__ == "__main__":
    main()
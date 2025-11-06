import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppComponent } from './app.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { FolderTreeComponent } from './components/folder-tree.component';
import { SearchFilesComponent } from './components/search-files.component';
import { LlmSettingsComponent } from './components/llm-settings.component';
import { ResearchHubComponent } from './components/research-hub.component';
import { NotebookViewComponent } from './components/notebook-view.component'; // Import NotebookViewComponent

import { MatTreeModule } from "@angular/material/tree";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { HttpClientModule } from "@angular/common/http";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatSelectModule } from "@angular/material/select";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatCardModule } from "@angular/material/card";
import { MatInputModule } from "@angular/material/input";
import { MatToolbarModule } from "@angular/material/toolbar";
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs'; // Import MatTabsModule
import { MatListModule } from '@angular/material/list'; // Import MatListModule

@NgModule({
  declarations: [
    AppComponent,
    FolderTreeComponent,
    LlmSettingsComponent
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    // Material Modules
    MatTreeModule,
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatSelectModule,
    MatFormFieldModule,
    MatCardModule,
    MatInputModule,
    MatToolbarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatTabsModule,
    MatListModule,
    // Standalone Components
    SearchFilesComponent,
    ResearchHubComponent,
    NotebookViewComponent
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {
}

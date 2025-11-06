import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientModule } from "@angular/common/http";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";

// Components
import { AppComponent } from './app.component';
import { FolderTreeComponent } from './components/folder-tree.component';
import { SearchFilesComponent } from './components/search-files.component';
import { LlmSettingsComponent } from './components/llm-settings.component';
import { ResearchHubComponent } from './components/research-hub.component';
import { NotebookViewComponent } from './components/notebook-view.component';

// Angular Material Modules
import { MatTreeModule } from "@angular/material/tree";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatSelectModule } from "@angular/material/select";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatCardModule } from "@angular/material/card";
import { MatInputModule } from "@angular/material/input";
import { MatToolbarModule } from "@angular/material/toolbar";
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatListModule } from '@angular/material/list';
import { MatOptionModule } from '@angular/material/core';

@NgModule({
  declarations: [
    AppComponent,
    FolderTreeComponent,
    LlmSettingsComponent,
    SearchFilesComponent // Declare non-standalone components
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,

    // Angular Material Modules needed by components in declarations
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatOptionModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatCardModule,
    MatCheckboxModule,
    MatTreeModule,
    MatToolbarModule,
    MatTabsModule,
    MatListModule,

    // Import standalone components
    ResearchHubComponent,
    NotebookViewComponent
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {
}
